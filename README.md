# SmartCAT CLI Tool
A command-line tool for working with the SmartCAT API – a platform for translation project management.
Based on the existing library: https://pypi.org/project/smartcat/ by v.zhyliaiev

## Installation

Environment variables (.env file):
```
SMARTCAT_USERNAME=your_username
SMARTCAT_PASSWORD=your_password
SMARTCAT_SERVER=eu  # або us
```

## Usage
Basic syntax
```
python smartcat_cli.py [GLOBAL_OPTIONS] COMMAND [SUBCOMMAND] [PARAMETERS]

Global parameters

--username - SmartCAT username  
--password - SmartCAT password  
--server {eu,us} - Server region (default: eu)
--env-file PATH - Path to .env файлу
```

# Commands
## Projects management
### Create project
```
python smartcat_cli.py project create "Project name" SOURCE_LANG TARGET_LANG1 [TARGET_LANG2 ...]

Parameters:

name - Project name  
source_lang - Source language code (e.g., en, uk, ru)  
target_langs - Target language codes (one or more)  
--assign-vendor - Assign to vendor  
--files FILE1 [FILE2 ...] - Files to attach  

Example:  
python smartcat_cli.py project create "My Project" en uk ru --files document.docx manual.pdf 
```

### Projects list
```
python smartcat_cli.py project list
```
### Get project information
```
python smartcat_cli.py project get PROJECT_ID
```
### Update project
```
python smartcat_cli.py project update PROJECT_ID [PARAMETERS]

Parameters:

--name - New project name  
--source-lang - New source language  
--target-langs LANG1 [LANG2 ...] - New target languages  

Example:  
python smartcat_cli.py project update 12345 --name "Updated Name" --target-langs uk ru de
```
### Delete project
```
python smartcat_cli.py project delete PROJECT_ID [--force]

Parameters:

--force - Skip confirmation
```
### Project statistics
```
python smartcat_cli.py project stats PROJECT_ID
```
### Attach documents to project
```
python smartcat_cli.py project attach PROJECT_ID FILE1 [FILE2 ...]

Example:

python smartcat_cli.py project attach 12345 document.docx translation.xlsx
```
### Add target language
```
python smartcat_cli.py project add-language PROJECT_ID LANGUAGE_CODE

Example:

python smartcat_cli.py project add-language 12345 de
```
### Cancel project
```
python smartcat_cli.py project cancel PROJECT_ID [--force]
```
### Restore project
```
python smartcat_cli.py project restore PROJECT_ID
```
## Documents management
### Get document information

```
python smartcat_cli.py document get DOCUMENT_ID
```
### Delete document
```
python smartcat_cli.py document delete DOCUMENT_ID [--force]
```
### Export documents
```
python smartcat_cli.py document export DOC_ID1 [DOC_ID2 ...] [--type {target,xliff}]

Parameters:

--type - Export type: `target` (translated files) or `xliff` (XLIFF format)  

Example:

python smartcat_cli.py document export 12345 67890 --type target
```
### Download export result
```
python smartcat_cli.py document download TASK_ID [--output FILENAME]

Parameters:

--output - Output filename (default: export_TASK_ID.zip)

Example:

python smartcat_cli.py document download abc123 --output my_translation.docx
```
### Update document
```
python smartcat_cli.py document update DOCUMENT_ID FILE1 [FILE2 ...]
```
### Rename document
```
python smartcat_cli.py document rename DOCUMENT_ID "New name"
```
### Translate document
```
python smartcat_cli.py document translate DOCUMENT_ID TRANSLATION_FILE1 [FILE2 ...]
```
### Translation status
```
python smartcat_cli.py document translate-status DOCUMENT_ID
```
## Language Codes
Use standard ISO language codes:

- en – English
- uk – Ukrainian
- ru – Russian
- de – German
- fr – French
- es – Spanish
- pl – Polish
- etc.

All HTTP responses are displayed with status codes and headers.
JSON responses are formatted for readability.
Missing files will raise an error with a message.
Delete operations require confirmation (unless --force is used).

### Security
Passwords are not stored in the config file.
Use .env files to securely store credentials.
Add .env to .gitignore in your projects.

### Troubleshooting
- Authentication error: Check username and password.
- Connection error: Ensure the correct server is selected (eu/us).
- File not found: Verify file paths.

### Help
For help on any command:
```
python cli.py --help
python cli.py project --help
python cli.py document --help
```