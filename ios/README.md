# THE VAULT for iPhone

The iOS target uses the production Vault site and its existing authentication and collection sync. The native barcode scanner opens the in-app search for a scanned UPC, EAN, or numeric Code 128 value. A value is searched as a catalog identifier. Availability depends on which catalog records supply a barcode.

## Build

1. On a Mac with Xcode and XcodeGen installed, run `xcodegen generate` from this directory.
2. Open `Vault.xcodeproj` and select the Apple Developer team under Signing & Capabilities. The bundle identifier is provisional until registered by the account holder.
3. Run the Vault scheme on an iPhone. Use a physical iPhone to test camera permission and scanning.

Verify first-run sign-in, guest use, password recovery, collection sync, barcode results and no-match behavior, and camera denial. An App Store submission still needs an account deletion flow, App Store assets and privacy disclosures, and a signed build tested on physical devices.
