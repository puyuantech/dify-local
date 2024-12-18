from core.tools.provider.builtin_tool_provider import BuiltinToolProviderController

class SendUrl(BuiltinToolProviderController):
    def _validate_credentials(self, credentials: dict) -> None:
        pass