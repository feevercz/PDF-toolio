# Original User Request

## Initial Request — 2026-07-28T15:02:43Z

<USER_REQUEST>
# Teamwork Project Prompt — Draft

A local desktop or web application for compressing PDF files. It allows users to load a PDF, view its name, preview, and original size, select from three compression levels (Basic, Large, Maximum) with estimated resulting sizes, and save the compressed file with a custom name and location.

Working directory: C:\Users\strak\teamwork_projects\pdf_compressor
Integrity mode: development

## Requirements

### R1. PDF Loading and Display
The application must allow the user to select and load a local PDF file. Once loaded, it must display the file's name, its original size on disk, and a visual preview (e.g., a thumbnail of the first page).

### R2. Compression Selection and Estimation
The user interface must present three distinct compression levels: Basic, Large, and Maximum. For each level, the application must display an estimated size of the resulting compressed PDF before the user confirms the action.

### R3. Compression and Saving
Upon confirming the compression level, the application must process the file, generating a new compressed PDF. The user must be able to specify the output file name and the location where the file will be saved.

## Acceptance Criteria

### Programmatic Verification
- [ ] A test script (`verify_compression.py` or similar) is provided and passes successfully. It must programmatically take a test PDF, apply the three compression levels, and assert that the resulting file sizes are smaller than the original file.

### Functional UI Verification
- [ ] The application launches successfully without crashing.
- [ ] A sample PDF can be loaded, and its preview, name, and original size are correctly displayed.
- [ ] Selecting different compression levels updates the UI or shows realistic estimated file sizes.
- [ ] Compressing and saving the file successfully writes a valid, compressed PDF to the specified destination.
</USER_REQUEST>

## Follow-up — 2026-07-28T15:33:54Z

USER FEEDBACK: The user tested the app on real PDFs and found the actual compression works perfectly. However, the size estimation is somewhat inaccurate. For 'Large', it estimated 1.2MB but actual was 700kb. For 'Basic', it estimated 5-10% reduction but actual was 0% reduction. Please adjust the estimation heuristics in pdf_engine.py slightly to better reflect these real-world results if you can, but do not let this block the completion of Phase 1. Finish your current test fixes first!

## Follow-up — 2026-07-28T15:39:13Z

<USER_REQUEST>
# Teamwork Project Prompt — Draft (Phase 2: Installer & Icon)

Create a standard Windows installer for the PDF-toolio application. The task involves packaging the Python app into a standalone executable, generating a modern minimalist icon, and creating an installer with an uninstaller and optional desktop shortcut.

Working directory: C:\Users\strak\Documents\app development\PDF-toolio
Integrity mode: development

## Requirements

### R1. Standalone Application Packaging
The existing Python application must be packaged into a standalone Windows executable (e.g., via PyInstaller) so that end-users do not need to install Python or any dependencies from `requirements.txt` manually.

### R2. Modern Minimalist Icon
A script must be created to generate a new, modern, and minimalist `.ico` file. The icon must feature two lines of text: "PDF" on the first line, and "toolio" on the second line. The "io" part of "toolio" must be in a different color than the rest of the text to distinguish it visually.

### R3. Windows Installer
A standard Windows installer must be created (using tools like Inno Setup compiler or NSIS, which can be scripted or downloaded if necessary, or using a Python-based installer builder). The installer must:
- Allow the user to choose the installation directory.
- Automatically generate an uninstaller.
- Provide an option to create a desktop shortcut (using the new icon).

## Acceptance Criteria

### Programmatic Verification
- [ ] A build script (`build_installer.py` or similar) is provided. It successfully executes the packaging process and compiles the installer, resulting in a valid `PDF-toolio-Setup.exe` file in the output directory.

### Functional UI Verification
- [ ] The generated installer runs on Windows without errors.
- [ ] The installer allows directory selection and offers a desktop shortcut option.
- [ ] After installation, the desktop shortcut correctly displays the new two-line, multi-colored icon.
- [ ] The installed application launches successfully without a command prompt window.
- [ ] The uninstaller successfully removes the application from the system.
</USER_REQUEST>

## Follow-up — 2026-07-28T20:44:42Z

<USER_REQUEST>
# Teamwork Project Prompt

A native iOS application (Swift / SwiftUI) for compressing PDF files. It allows users to pick a PDF, select from three compression levels, and compresses the file locally on the device (no backend), saving or sharing the result. The iOS app resides in a dedicated subfolder of an existing project with its own git repository.

Working directory: C:\Users\strak\Documents\app development\PDF-toolio\mobile_app_ios
Integrity mode: development

## Requirements

### R1. Repository and Workspace Setup
Create a new subfolder `mobile_app_ios` within the parent directory. Initialize a completely separate git repository inside `mobile_app_ios`. Update the parent directory's `.gitignore` to explicitly ignore the `mobile_app_ios` folder so the projects remain unlinked.

### R2. PDF Loading and Display
The iOS application must allow the user to pick a local PDF file from their device storage (e.g., via standard iOS document picker). Once loaded, it must display the file's name, its original size, and a visual preview.

### R3. Local On-Device Compression
The user interface must present three compression levels: Basic, Large, and Maximum, along with estimated resulting sizes. The compression must be executed **locally on the device** (using native iOS frameworks like PDFKit, Quartz/CoreGraphics, or a local Swift library). No cloud backend is permitted.

### R4. Export and Share
Upon completing the compression, the application must allow the user to save the compressed PDF back to their device files or share it via the native iOS share sheet (UIActivityViewController).

## Acceptance Criteria

### Programmatic Verification
- [ ] The parent repository's `.gitignore` contains `mobile_app_ios/`.
- [ ] The `mobile_app_ios` folder contains a valid, independent `.git` directory.
- [ ] The iOS project successfully builds/compiles via `xcodebuild` (or standard Swift build tools) without crashing.
- [ ] A programmatic test or script (e.g., XCTest testing the compression module) is provided and passes, proving that the local compression logic successfully reduces the file size of a sample PDF.

### Functional Verification
- [ ] The application can be built and launched on an iOS simulator.
- [ ] A sample PDF can be selected, and its preview is shown.
- [ ] The compression runs locally (even without internet access) and produces a valid, smaller PDF file.
</USER_REQUEST>

