import argparse
import json
import sys

from .client import WhatsAppCloudClient
from .config import WhatsAppConfig
from .server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WhatsApp Cloud API bridge CLI.")
    parser.add_argument("--phone-number-id", help="WhatsApp phone number ID (overrides env)")
    parser.add_argument("--token", help="WhatsApp access token (overrides env)")
    parser.add_argument("--app-secret", help="App secret for signature verification (overrides env)")
    parser.add_argument("--verify-token", help="Verification token used for webhook challenge (overrides env)")

    sub = parser.add_subparsers(dest="command", required=True)

    send_text = sub.add_parser("send-text", help="Send a text message via Cloud API")
    send_text.add_argument("--to", required=True, help="Destination phone number, e.g. 15551234567")
    send_text.add_argument("--text", required=True, help="Text body to send")
    send_text.add_argument("--preview-url", action="store_true", help="Allow URL previews in message")

    upload_media = sub.add_parser("upload-media", help="Upload a media file and return media ID")
    upload_media.add_argument("--file", required=True, help="Path to media file")
    upload_media.add_argument("--mime-type", help="Optional MIME type override")

    send_media = sub.add_parser("send-media", help="Send a previously uploaded media by ID")
    send_media.add_argument("--to", required=True, help="Destination phone number, e.g. 15551234567")
    send_media.add_argument("--media-id", required=True, help="Media ID returned from upload-media")
    send_media.add_argument("--media-type", choices=["image", "video", "audio", "document"], default="image")
    send_media.add_argument("--caption", help="Optional caption for the media")

    download_media = sub.add_parser("download-media", help="Download media from a media URL")
    download_media.add_argument("--url", required=True, help="Media URL provided by Cloud API")
    download_media.add_argument("--dest", help="Destination path; defaults to filename derived from URL")

    runserver_cmd = sub.add_parser("runserver", help="Start webhook server with FastAPI/uvicorn")
    runserver_cmd.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    runserver_cmd.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    runserver_cmd.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")

    # Add 'serve' alias for runserver
    serve_cmd = sub.add_parser("serve", help="Start webhook server (alias for runserver)")
    serve_cmd.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    serve_cmd.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    serve_cmd.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")

    return parser


def resolve_config(args: argparse.Namespace) -> WhatsAppConfig:
    # Explicit CLI values take precedence; otherwise fall back to env.
    if args.phone_number_id and args.token:
        return WhatsAppConfig(
            phone_number_id=args.phone_number_id,
            access_token=args.token,
            app_secret=args.app_secret,
            verify_token=args.verify_token,
        )

    cfg = WhatsAppConfig.from_env()
    return cfg.with_override(
        phone_number_id=args.phone_number_id,
        access_token=args.token,
        app_secret=args.app_secret,
        verify_token=args.verify_token,
    )


def handle_send_text(args: argparse.Namespace) -> int:
    cfg = resolve_config(args)
    client = WhatsAppCloudClient(cfg)
    response = client.send_text(args.to, args.text, preview_url=args.preview_url)
    print(json.dumps(response.json(), indent=2))
    return 0


def handle_upload_media(args: argparse.Namespace) -> int:
    cfg = resolve_config(args)
    client = WhatsAppCloudClient(cfg)
    meta = client.upload_media(args.file, mime_type=args.mime_type)
    print(json.dumps(meta, indent=2))
    return 0


def handle_send_media(args: argparse.Namespace) -> int:
    cfg = resolve_config(args)
    client = WhatsAppCloudClient(cfg)
    response = client.send_media(
        args.to,
        media_id=args.media_id,
        media_type=args.media_type,
        caption=args.caption,
    )
    print(json.dumps(response.json(), indent=2))
    return 0


def handle_download_media(args: argparse.Namespace) -> int:
    cfg = resolve_config(args)
    client = WhatsAppCloudClient(cfg)
    path = client.download_media(args.url, dest_path=args.dest)
    print(json.dumps({"saved_to": str(path)}, indent=2))
    return 0


def handle_runserver(args: argparse.Namespace) -> int:
    # run_server loads config from env/overrides within app_factory
    run_server(host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "send-text": handle_send_text,
        "upload-media": handle_upload_media,
        "send-media": handle_send_media,
        "download-media": handle_download_media,
        "runserver": handle_runserver,
        "serve": handle_runserver,  # Alias for runserver
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.error("Unknown command")
    try:
        code = handler(args)
    except Exception as exc:  # pragma: no cover
        parser.error(str(exc))
        return
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
