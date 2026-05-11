# Resume Generator

Resume Generator is a desktop GUI for turning a master LaTeX resume into tailored output files. It is designed for the common workflow of keeping one source resume and producing multiple generated variants by selecting different sections or entries.

The application focuses on two persistent artifacts:

- A source LaTeX resume file.
- A link library that stores the source snapshot and every generated file derived from it.

## What The App Does

The GUI lets you load either a source resume or an existing link library, inspect the parsed sections and entries, choose what should stay in the output, and then write a new generated `.tex` file. Each generated file is recorded in the link library so the source and its outputs stay connected over time.

## Assumptions

This project assumes:

- The source file is a LaTeX resume that matches the structure in [this resume template](https://www.overleaf.com/latex/templates/cs-slash-it-slash-swe-resume-template/ncxgzcgknkmf)
- The resume contains recognizable section and entry commands that the parser can extract.
- The source file has all content, generated files are derived snapshots.

## How To Use The GUI

1. Launch the app.
2. Click `Upload Source File` and choose a `.tex` resume.
3. Review the parsed sections in the left panel.
4. Toggle section and entry checkboxes to choose what should appear in the output.
5. Click `Update Links` to save or refresh the link library for the current source.
6. Click `Generate` to create a new generated `.tex` file and register it in the link library.
7. If you already have a saved link library, click `Upload Link Library` instead of starting from scratch.
8. After loading a link library, the app restores the associated source file and its saved generated-file history.

### UI Behavior

- `Upload Source File` loads and parses a source resume.
- `Upload Link Library` loads a saved link library and reconnects it to its source file when possible.
- `Update Links` saves the current source snapshot into the library without creating a new output file.
- `Generate` creates a new output file using the current selections and stores a matching generated-file entry in the library.
- The app shows the currently loaded source file and library file in the top bar.

### Where The File Is Stored

The default library path is derived from the source file name and stored alongside the source file. For a source file like `resume.tex`, the default library becomes `resume.resume-links.json` in the same folder.

#### resume-links.json

The JSON snapshot is the source of truth for the relationship between one master resume and many generated variants. It makes it possible to reopen the project later, see the previously generated outputs, and rebuild new variants from the same source structure.

### How Updates Work

- Loading a source file creates an in-memory `SourceFile`.
- Clicking `Update Links` writes the current source snapshot into the link library JSON file.
- Clicking `Generate` creates a new `GeneratedFile`, writes it to disk as `.tex`, adds it to the link library, and saves the updated JSON file.
- If the source file is reopened after a link library has been loaded, the app preserves the saved selection state where possible.
