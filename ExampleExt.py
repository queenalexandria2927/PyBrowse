EXTENSION_NAME = "My Cool Extension"

def init_extension(browser):
    # This runs when loaded.
    print("Extension loaded!")
    # You can add UI, hook events, etc. with `browser`.

def cleanup_extension(browser):
    # This runs on unload.
    print("Extension unloaded!")
