"""
SmartCAT CLI Tool
~~~~~~~~~~~~~~~~~

Command line interface for SmartCAT API operations
"""

import argparse
import json
import sys
import os
import mimetypes
from getpass import getpass
from api import SmartCAT
from dotenv import load_dotenv

try:
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def get_content_type(file_path):
    """Get content type for file based on extension"""
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        # Default content type for unknown files
        content_type = "application/octet-stream"
    return content_type


def prepare_files_with_content_type(file_paths):
    """Prepare files dictionary with proper content types"""
    files = {}
    for file_path in file_paths:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            content_type = get_content_type(file_path)
            file_obj = open(file_path, "rb")
            # Format: (filename, file_object, content_type)
            files[filename] = (filename, file_obj, content_type)
        else:
            print(f"Error: File not found: {file_path}")
            return None
    return files


def close_files(files):
    """Close all file objects in files dictionary"""
    for file_tuple in files.values():
        if hasattr(file_tuple[1], "close"):
            file_tuple[1].close()


def load_config():
    """Load configuration from .env file, config file or environment variables"""
    config = {}

    # Load .env file if available
    if DOTENV_AVAILABLE:
        # Look for .env file in current directory first, then home directory
        env_files = [".env", os.path.expanduser("~/.env")]
        for env_file in env_files:
            if os.path.exists(env_file):
                load_dotenv(env_file)
                print(f"Loaded environment from: {env_file}")
                break
    else:
        # Check if .env file exists and warn user
        if os.path.exists(".env") or os.path.exists(os.path.expanduser("~/.env")):
            print("Warning: .env file found but python-dotenv is not installed.")
            print("Install it with: pip install python-dotenv")

    # Try to load from config file
    config_file = os.path.expanduser("~/.smartcat_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")

    # Override with environment variables if present
    if "SMARTCAT_USERNAME" in os.environ:
        config["username"] = os.environ["SMARTCAT_USERNAME"]
    if "SMARTCAT_PASSWORD" in os.environ:
        config["password"] = os.environ["SMARTCAT_PASSWORD"]
    if "SMARTCAT_SERVER" in os.environ:
        config["server"] = os.environ["SMARTCAT_SERVER"]

    return config


def save_config(username, server):
    """Save configuration to config file (without password)"""
    config_file = os.path.expanduser("~/.smartcat_config.json")
    config = {"username": username, "server": server}
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        print(f"Configuration saved to {config_file}")
    except Exception as e:
        print(f"Warning: Could not save config: {e}")


def get_credentials():
    """Get credentials from user input or config"""
    config = load_config()

    username = config.get("username")
    if not username:
        username = input("SmartCAT Username: ")

    password = config.get("password")
    if not password:
        password = getpass("SmartCAT Password: ")

    server = config.get("server", SmartCAT.SERVER_EUROPE)

    return username, password, server


def format_response(response):
    """Format HTTP response for display"""
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")

    try:
        if response.content:
            # Try to parse as JSON
            json_data = response.json()
            print("Response Body:")
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
    except:
        # If not JSON, print as text
        if response.text:
            print("Response Body:")
            print(response.text)


def cmd_project_create(args, api):
    """Create a new project"""
    project_data = {
        "name": args.name,
        "sourceLanguage": args.source_lang,
        "targetLanguages": args.target_langs,
        "assignToVendor": args.assign_vendor,
    }

    files = {}
    if args.files:
        files = prepare_files_with_content_type(args.files)
        if files is None:
            return

    print(f"Creating project: {args.name}")
    try:
        response = api.project.create(data=project_data, files=files)
        format_response(response)
    finally:
        # Close file handles
        if files:
            close_files(files)


def cmd_project_list(args, api):
    """List all projects"""
    print("Getting all projects...")
    response = api.project.get_all()
    format_response(response)


def cmd_project_get(args, api):
    """Get project by ID"""
    print(f"Getting project: {args.id}")
    response = api.project.get(args.id)
    format_response(response)


def cmd_project_update(args, api):
    """Update project"""
    project_data = {}
    if args.name:
        project_data["name"] = args.name
    if args.source_lang:
        project_data["sourceLanguage"] = args.source_lang
    if args.target_langs:
        project_data["targetLanguages"] = args.target_langs

    print(f"Updating project: {args.id}")
    response = api.project.update(args.id, project_data)
    format_response(response)


def cmd_project_delete(args, api):
    """Delete project"""
    if not args.force:
        confirm = input(f"Are you sure you want to delete project {args.id}? (y/N): ")
        if confirm.lower() != "y":
            print("Operation cancelled")
            return

    print(f"Deleting project: {args.id}")
    response = api.project.delete(args.id)
    format_response(response)


def cmd_project_stats(args, api):
    """Get project statistics"""
    print(f"Getting statistics for project: {args.id}")
    response = api.project.completed_work_statistics(args.id)
    format_response(response)


def cmd_document_get(args, api):
    """Get document by ID"""
    print(f"Getting document: {args.id}")
    response = api.document.get(args.id)
    format_response(response)


def cmd_document_delete(args, api):
    """Delete document"""
    if not args.force:
        confirm = input(f"Are you sure you want to delete document {args.id}? (y/N): ")
        if confirm.lower() != "y":
            print("Operation cancelled")
            return

    print(f"Deleting document: {args.id}")
    response = api.document.delete(args.id)
    format_response(response)


def cmd_document_export(args, api):
    """Export documents"""
    document_ids = args.document_ids
    target_type = args.type or "target"

    print(f"Requesting export for documents: {', '.join(document_ids)}")
    print(f"Export type: {target_type}")

    response = api.document.request_export(document_ids, target_type)
    format_response(response)


def cmd_document_download(args, api):
    """Download export result"""
    print(f"Downloading export result: {args.task_id}")
    response = api.document.download_export_result(args.task_id)

    if response.status_code == 200:
        output_file = args.output or f"export_{args.task_id}.zip"
        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"File downloaded: {output_file}")
    else:
        format_response(response)


def cmd_project_attach_document(args, api):
    """Attach document to project"""
    files = prepare_files_with_content_type(args.files)
    if files is None:
        return

    print(f"Attaching documents to project: {args.project_id}")
    try:
        response = api.project.attach_document(args.project_id, files)
        format_response(response)
    finally:
        # Close file handles
        close_files(files)


def cmd_project_add_language(args, api):
    """Add target language to project"""
    print(f"Adding language {args.language} to project: {args.project_id}")
    response = api.project.add_target_lang(args.project_id, args.language)
    format_response(response)


def cmd_project_cancel(args, api):
    """Cancel project"""
    if not args.force:
        confirm = input(f"Are you sure you want to cancel project {args.id}? (y/N): ")
        if confirm.lower() != "y":
            print("Operation cancelled")
            return

    print(f"Cancelling project: {args.id}")
    response = api.project.cancel(args.id)
    format_response(response)


def cmd_project_restore(args, api):
    """Restore project"""
    print(f"Restoring project: {args.id}")
    response = api.project.restore(args.id)
    format_response(response)


def cmd_document_update(args, api):
    """Update document"""
    files = prepare_files_with_content_type(args.files)
    if files is None:
        return

    print(f"Updating document: {args.id}")
    try:
        response = api.document.update(args.id, files)
        format_response(response)
    finally:
        # Close file handles
        close_files(files)


def cmd_document_rename(args, api):
    """Rename document"""
    print(f"Renaming document {args.id} to: {args.name}")
    response = api.document.rename(args.id, args.name)
    format_response(response)


def cmd_document_translate(args, api):
    """Translate document using uploaded translation file"""
    files = prepare_files_with_content_type(args.files)
    if files is None:
        return

    print(f"Translating document: {args.id}")
    try:
        response = api.document.translate(args.id, files)
        format_response(response)
    finally:
        # Close file handles
        close_files(files)


def cmd_document_translate_status(args, api):
    """Get translation status"""
    print(f"Getting translation status for document: {args.id}")
    response = api.document.get_translation_status(args.id)
    format_response(response)


def main():
    parser = argparse.ArgumentParser(description="SmartCAT CLI Tool")
    parser.add_argument("--username", help="SmartCAT username")
    parser.add_argument("--password", help="SmartCAT password")
    parser.add_argument(
        "--server", choices=["eu", "us"], default="eu", help="Server region (eu/us)"
    )
    parser.add_argument("--env-file", help="Path to .env file")
    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save username and server to config file",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Project commands
    project_parser = subparsers.add_parser("project", help="Project operations")
    project_subparsers = project_parser.add_subparsers(dest="project_action")

    # Project create
    create_parser = project_subparsers.add_parser("create", help="Create project")
    create_parser.add_argument("name", help="Project name")
    create_parser.add_argument("source_lang", help="Source language code")
    create_parser.add_argument("target_langs", nargs="+", help="Target language codes")
    create_parser.add_argument(
        "--assign-vendor", action="store_true", help="Assign to vendor"
    )
    create_parser.add_argument("--files", nargs="*", help="Files to attach")

    # Project list
    project_subparsers.add_parser("list", help="List all projects")

    # Project get
    get_parser = project_subparsers.add_parser("get", help="Get project by ID")
    get_parser.add_argument("id", help="Project ID")

    # Project update
    update_parser = project_subparsers.add_parser("update", help="Update project")
    update_parser.add_argument("id", help="Project ID")
    update_parser.add_argument("--name", help="New project name")
    update_parser.add_argument("--source-lang", help="New source language")
    update_parser.add_argument("--target-langs", nargs="*", help="New target languages")

    # Project delete
    delete_parser = project_subparsers.add_parser("delete", help="Delete project")
    delete_parser.add_argument("id", help="Project ID")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")

    # Project stats
    stats_parser = project_subparsers.add_parser("stats", help="Get project statistics")
    stats_parser.add_argument("id", help="Project ID")

    # Project attach document
    attach_parser = project_subparsers.add_parser(
        "attach", help="Attach document to project"
    )
    attach_parser.add_argument("project_id", help="Project ID")
    attach_parser.add_argument("files", nargs="+", help="Files to attach")

    # Project add language
    addlang_parser = project_subparsers.add_parser(
        "add-language", help="Add target language"
    )
    addlang_parser.add_argument("project_id", help="Project ID")
    addlang_parser.add_argument("language", help="Language code (e.g., uk, ru, de)")

    # Project cancel
    cancel_parser = project_subparsers.add_parser("cancel", help="Cancel project")
    cancel_parser.add_argument("id", help="Project ID")
    cancel_parser.add_argument("--force", action="store_true", help="Skip confirmation")

    # Project restore
    restore_parser = project_subparsers.add_parser("restore", help="Restore project")
    restore_parser.add_argument("id", help="Project ID")

    # Document commands
    doc_parser = subparsers.add_parser("document", help="Document operations")
    doc_subparsers = doc_parser.add_subparsers(dest="document_action")

    # Document get
    doc_get_parser = doc_subparsers.add_parser("get", help="Get document by ID")
    doc_get_parser.add_argument("id", help="Document ID")

    # Document delete
    doc_delete_parser = doc_subparsers.add_parser("delete", help="Delete document")
    doc_delete_parser.add_argument("id", help="Document ID")
    doc_delete_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation"
    )

    # Document export
    export_parser = doc_subparsers.add_parser("export", help="Export documents")
    export_parser.add_argument("document_ids", nargs="+", help="Document IDs")
    export_parser.add_argument(
        "--type", choices=["target", "xliff"], help="Export type (target/xliff)"
    )

    # Document download
    download_parser = doc_subparsers.add_parser(
        "download", help="Download export result"
    )
    download_parser.add_argument("task_id", help="Export task ID")
    download_parser.add_argument("--output", help="Output file name")

    # Document update
    doc_update_parser = doc_subparsers.add_parser("update", help="Update document")
    doc_update_parser.add_argument("id", help="Document ID")
    doc_update_parser.add_argument("files", nargs="+", help="Files to update with")

    # Document rename
    rename_parser = doc_subparsers.add_parser("rename", help="Rename document")
    rename_parser.add_argument("id", help="Document ID")
    rename_parser.add_argument("name", help="New document name")

    # Document translate
    translate_parser = doc_subparsers.add_parser("translate", help="Translate document")
    translate_parser.add_argument("id", help="Document ID")
    translate_parser.add_argument("files", nargs="+", help="Translation files")

    # Document translation status
    status_parser = doc_subparsers.add_parser(
        "translate-status", help="Get translation status"
    )
    status_parser.add_argument("id", help="Document ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load specific .env file if provided
    if args.env_file and DOTENV_AVAILABLE:
        if os.path.exists(args.env_file):
            load_dotenv(args.env_file)
            print(f"Loaded environment from: {args.env_file}")
        else:
            print(f"Error: .env file not found: {args.env_file}")
            sys.exit(1)

    # Get credentials
    if args.username and args.password:
        username, password = args.username, args.password
    else:
        username, password, _ = get_credentials()

    # Determine server
    server_url = SmartCAT.SERVER_EUROPE if args.server == "eu" else SmartCAT.SERVER_USA

    # Save config if requested
    if args.save_config:
        save_config(username, server_url)

    # Initialize API
    try:
        api = SmartCAT(username, password, server_url)

        print(f"Connected to SmartCAT ({args.server.upper()})")
    except Exception as e:
        print(f"Error connecting to SmartCAT: {e}")
        sys.exit(1)

    # Execute command
    try:
        if args.command == "project":
            if args.project_action == "create":
                cmd_project_create(args, api)
            elif args.project_action == "list":
                cmd_project_list(args, api)
            elif args.project_action == "get":
                cmd_project_get(args, api)
            elif args.project_action == "update":
                cmd_project_update(args, api)
            elif args.project_action == "delete":
                cmd_project_delete(args, api)
            elif args.project_action == "stats":
                cmd_project_stats(args, api)
            elif args.project_action == "attach":
                cmd_project_attach_document(args, api)
            elif args.project_action == "add-language":
                cmd_project_add_language(args, api)
            elif args.project_action == "cancel":
                cmd_project_cancel(args, api)
            elif args.project_action == "restore":
                cmd_project_restore(args, api)
            else:
                project_parser.print_help()

        elif args.command == "document":
            if args.document_action == "get":
                cmd_document_get(args, api)
            elif args.document_action == "delete":
                cmd_document_delete(args, api)
            elif args.document_action == "export":
                cmd_document_export(args, api)
            elif args.document_action == "download":
                cmd_document_download(args, api)
            elif args.document_action == "update":
                cmd_document_update(args, api)
            elif args.document_action == "rename":
                cmd_document_rename(args, api)
            elif args.document_action == "translate":
                cmd_document_translate(args, api)
            elif args.document_action == "translate-status":
                cmd_document_translate_status(args, api)
            else:
                doc_parser.print_help()

    except Exception as e:
        print(f"Error executing command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
