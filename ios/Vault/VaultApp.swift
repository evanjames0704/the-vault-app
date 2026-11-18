import AVFoundation
import SwiftUI
import UIKit
import VisionKit
import WebKit

@main
struct VaultApp: App {
    var body: some Scene {
        WindowGroup { VaultScreen() }
    }
}

@MainActor
struct VaultScreen: View {
    @StateObject private var vault = VaultSession()
    @State private var scanning = false
    @State private var message: String?
    private let gold = Color(red: 0.85, green: 0.69, blue: 0.38)

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("THE VAULT").font(.headline.weight(.semibold)).accessibilityAddTraits(.isHeader)
                Spacer()
                Button {
                    Task { await openScanner() }
                } label: {
                    Label("Scan barcode", systemImage: "barcode.viewfinder")
                }
            }
            .padding()
            .foregroundStyle(gold)
            .background(.black)
            ZStack {
                VaultWebView(webView: vault.webView)
                if vault.loading {
                    ProgressView("Opening THE VAULT").padding().background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
                if let error = vault.loadError {
                    VStack(spacing: 12) {
                        Text("Couldn’t open THE VAULT").font(.headline)
                        Text(error).font(.footnote).multilineTextAlignment(.center)
                        Button("Try again") { vault.load() }
                            .buttonStyle(.borderedProminent)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color.black)
                }
            }
        }
        .preferredColorScheme(.dark)
        .sheet(isPresented: $scanning) {
            NavigationStack {
                BarcodeScanner { result in
                    scanning = false
                    switch result {
                    case .success(let code):
                        Task {
                            do { try await vault.search(barcode: code) }
                            catch { message = error.localizedDescription }
                        }
                    case .failure(let error):
                        message = error.localizedDescription
                    }
                }
                .ignoresSafeArea(edges: .bottom)
                .navigationTitle("Scan a collectible barcode")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") { scanning = false }
                    }
                }
            }
        }
        .alert("THE VAULT", isPresented: Binding(
            get: { message != nil },
            set: { if !$0 { message = nil } }
        )) {
            Button("OK", role: .cancel) { message = nil }
        } message: {
            Text(message ?? "")
        }
    }

    @MainActor private func openScanner() async {
        guard DataScannerViewController.isSupported else {
            message = "Barcode scanning isn’t available on this iPhone. Enter the code in Add Item search."
            return
        }
        let access = AVCaptureDevice.authorizationStatus(for: .video)
        let granted: Bool
        if access == .notDetermined {
            granted = await AVCaptureDevice.requestAccess(for: .video)
        } else {
            granted = access == .authorized
        }
        guard granted, DataScannerViewController.isAvailable else {
            message = "The scanner needs camera access. You can enable it in Settings or enter the code in Add Item search."
            return
        }
        scanning = true
    }

}

@MainActor
final class VaultSession: NSObject, ObservableObject, WKNavigationDelegate {
    private static let origin = URL(string: "https://the-vault-v123-test.pages.dev/")!
    @Published private(set) var loading = true
    @Published private(set) var loadError: String?
    let webView = WKWebView(frame: .zero, configuration: WKWebViewConfiguration())

    override init() {
        super.init()
        webView.navigationDelegate = self
        webView.isOpaque = false
        webView.backgroundColor = .black
        load()
    }

    func load() {
        loading = true
        loadError = nil
        webView.load(URLRequest(url: Self.origin))
    }

    func search(barcode: String) async throws {
        guard let url = webView.url, isVaultOrigin(url), !loading, loadError == nil else {
            throw VaultError.catalogUnavailable
        }
        let result = try await webView.callAsyncJavaScript(
            """
            const add = document.getElementById('v13homeadd');
            const input = document.getElementById('v11q');
            const search = document.getElementById('v11go');
            if (!add || !input || !search || document.body.classList.contains('vault-onboarding')) {
                return false;
            }
            add.click();
            input.value = code;
            search.click();
            return true;
            """,
            arguments: ["code": barcode],
            in: nil,
            contentWorld: .page
        )
        guard result as? Bool == true else { throw VaultError.catalogUnavailable }
    }

    private func isVaultOrigin(_ url: URL) -> Bool {
        url.scheme == "https" && url.host == Self.origin.host && (url.port == nil || url.port == 443)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        if isVaultOrigin(url) {
            if navigationAction.targetFrame == nil {
                decisionHandler(.cancel)
                webView.load(navigationAction.request)
            } else {
                decisionHandler(.allow)
            }
            return
        }
        decisionHandler(.cancel)
        if navigationAction.navigationType == .linkActivated, url.scheme == "https" {
            UIApplication.shared.open(url)
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        loading = false
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        showLoadError(error)
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        showLoadError(error)
    }

    private func showLoadError(_ error: Error) {
        guard (error as NSError).code != NSURLErrorCancelled else { return }
        loading = false
        loadError = "Check your internet connection and try again."
    }
}

private struct VaultWebView: UIViewRepresentable {
    let webView: WKWebView

    func makeUIView(context: Context) -> WKWebView { webView }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}

private enum VaultError: LocalizedError {
    case catalogUnavailable
    case cameraUnavailable

    var errorDescription: String? {
        switch self {
        case .catalogUnavailable:
            return "Open THE VAULT and sign in or continue as a guest before scanning."
        case .cameraUnavailable:
            return "The scanner couldn’t start. Enter the barcode in Add Item search."
        }
    }
}

private struct BarcodeScanner: UIViewControllerRepresentable {
    let finished: (Result<String, Error>) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(finished: finished) }

    func makeUIViewController(context: Context) -> ScannerHost {
        let controller = DataScannerViewController(
            recognizedDataTypes: [.barcode(symbologies: [.ean8, .ean13, .itf14, .code128])],
            qualityLevel: .balanced,
            recognizesMultipleItems: false,
            isHighFrameRateTrackingEnabled: false,
            isPinchToZoomEnabled: true,
            isGuidanceEnabled: true,
            isHighlightingEnabled: true
        )
        controller.delegate = context.coordinator
        return ScannerHost(scanner: controller, coordinator: context.coordinator)
    }

    func updateUIViewController(_ uiViewController: ScannerHost, context: Context) {}

    @MainActor
    final class ScannerHost: UIViewController {
        let scanner: DataScannerViewController
        private let coordinator: Coordinator

        init(scanner: DataScannerViewController, coordinator: Coordinator) {
            self.scanner = scanner
            self.coordinator = coordinator
            super.init(nibName: nil, bundle: nil)
        }

        @available(*, unavailable)
        required init?(coder: NSCoder) { fatalError("Use init(scanner:coordinator:)") }

        override func viewDidLoad() {
            super.viewDidLoad()
            addChild(scanner)
            scanner.view.frame = view.bounds
            scanner.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
            view.addSubview(scanner.view)
            scanner.didMove(toParent: self)
        }

        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            do { try scanner.startScanning() }
            catch { coordinator.complete(.failure(VaultError.cameraUnavailable)) }
        }

        override func viewWillDisappear(_ animated: Bool) {
            scanner.stopScanning()
            super.viewWillDisappear(animated)
        }
    }

    @MainActor
    final class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let finished: (Result<String, Error>) -> Void
        private var didFinish = false

        init(finished: @escaping (Result<String, Error>) -> Void) { self.finished = finished }

        func complete(_ result: Result<String, Error>) {
            guard !didFinish else { return }
            didFinish = true
            finished(result)
        }

        func dataScanner(_ dataScanner: DataScannerViewController, didAdd addedItems: [RecognizedItem],
                         allItems: [RecognizedItem]) {
            for item in addedItems {
                guard case .barcode(let barcode) = item,
                      let code = barcode.payloadStringValue,
                      code.range(of: "^(?:[0-9]{8}|[0-9]{12,14})$", options: .regularExpression) != nil else { continue }
                dataScanner.stopScanning()
                complete(.success(code))
                return
            }
        }

        func dataScanner(_ dataScanner: DataScannerViewController,
                         becameUnavailableWithError error: DataScannerViewController.ScanningUnavailable) {
            complete(.failure(VaultError.cameraUnavailable))
        }
    }
}
