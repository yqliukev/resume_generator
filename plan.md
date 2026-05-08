A persistence file holds a dict of many generated files for a SourceFile. This is already represented by LinkLibrary class. 

Each LinkLibrary has one SourceFile (and vice versa), and can have many GeneratedFiles. Users can "Upload Source File" or "Upload Link Library" for different functionality. Two more buttons are needed: Update Links and Generate.
## SourceFile (tex) opened:
    - Update Links: generate a new LinkLibrary file for the sourcefile.
        - Auto-generate the LinkLibrary file name.
    - Generate clicked: 
        1. Generate new GeneratedFile entry in LinkLibrary
        2. Generate the actual GeneratedFile
## LinkLibrary (json) is opened:
    - Update Links: parse through the SourceFile and update all linked GeneratedFiles and LinkLibrary info on SourceFile 
        1. Update LinkLibrary with new SourceFile
        2. Use LinkLibrary to update GeneratedFiles
    - Generate pressed: a new link and file is generated 



<Tasks>