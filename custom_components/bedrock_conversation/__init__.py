"""AWS Bedrock Conversation integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol
import logging
import asyncio

# Essential imports
from .const import (
    DOMAIN, 
    HOME_LLM_API_ID,
    SERVICE_TOOL_NAME,
    SERVICE_TOOL_ALLOWED_DOMAINS,
    SERVICE_TOOL_ALLOWED_SERVICES,
)
from .bedrock_client import BedrockClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CONVERSATION]

# Allowed arguments for service calls
ALLOWED_SERVICE_CALL_ARGUMENTS = [
    "brightness",
    "brightness_pct",
    "rgb_color",
    "temperature",
    "hvac_mode",
    "target_temp_high",
    "target_temp_low",
    "fan_mode",
    "preset_mode",
    "humidity",
    "position",
    "tilt_position",
    "volume_level",
    "media_content_id",
    "media_content_type",
    "value",
]


class HassServiceTool(llm.Tool):
    """Tool for calling Home Assistant services."""

    name = SERVICE_TOOL_NAME
    description = (
        "Calls a Home Assistant service to control a specific device. "
        "You MUST provide the exact entity_id from the device list in the system prompt. "
        "Use this tool after identifying the correct device from the user's natural language request. "
        "For example: if user says 'turn on the lamp', find the entity_id containing 'lamp' from the device list, "
        "then call this tool with service='light.turn_on' and target_device='light.lamp_entity_id'."
    )

    parameters = vol.Schema(
        {
            vol.Required("service"): str,
            vol.Required("target_device"): str,
        }
    )

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the tool."""
        self.hass = hass

    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> dict:
        """Call the Home Assistant service."""
        # EMERGENCY DEBUG: Print to ensure this is being called
        print(f"\n{'='*80}")
        print(f"TOOL CALLED: {tool_input.tool_args}")
        print(f"{'='*80}\n")
        
        service = tool_input.tool_args.get("service")
        target_device = tool_input.tool_args.get("target_device")

        # Use ERROR level to ensure it shows up
        _LOGGER.error("🔧 TOOL CALL START: service=%s, device=%s", service, target_device)

        if not service or not target_device:
            error_msg = "Missing required parameters: service and target_device"
            _LOGGER.error("❌ Service call failed: %s", error_msg)
            return {
                "result": "error",
                "error": error_msg,
            }

        # Validate service
        try:
            domain, service_name = service.split(".", 1)
        except ValueError:
            error_msg = f"Invalid service format: {service}. Expected 'domain.service'"
            _LOGGER.error("❌ Service call failed: %s", error_msg)
            return {
                "result": "error",
                "error": error_msg,
            }

        # Check if domain is allowed
        if domain not in SERVICE_TOOL_ALLOWED_DOMAINS:
            error_msg = f"Service domain '{domain}' is not allowed"
            _LOGGER.error("❌ Service call failed: %s", error_msg)
            return {
                "result": "error",
                "error": error_msg,
            }

        # Check if service is allowed
        if service not in SERVICE_TOOL_ALLOWED_SERVICES:
            error_msg = f"Service '{service}' is not allowed"
            _LOGGER.error("❌ Service call failed: %s", error_msg)
            return {
                "result": "error",
                "error": error_msg,
            }

        # Build service data
        service_data = {ATTR_ENTITY_ID: target_device}

        # Add allowed additional arguments
        for key, value in tool_input.tool_args.items():
            if key in ALLOWED_SERVICE_CALL_ARGUMENTS:
                service_data[key] = value

        _LOGGER.error("📤 CALLING SERVICE: %s.%s with data: %s", domain, service_name, service_data)

        try:
            # Add timeout protection
            async with asyncio.timeout(5.0):
                _LOGGER.error("⏱️ Starting service call with 5s timeout...")
                
                # CRITICAL FIX: Use blocking=False to prevent hanging
                await hass.services.async_call(
                    domain,
                    service_name,
                    service_data,
                    blocking=False,  # ✅ FIXED: Non-blocking to prevent infinite hang
                )
                
                _LOGGER.error("⏱️ Service call returned (non-blocking)")
            
            success_msg = f"✅ Successfully called {service} on {target_device}"
            _LOGGER.error(success_msg)
            
            print(f"\n{'='*80}")
            print(f"TOOL SUCCESS: {success_msg}")
            print(f"{'='*80}\n")
            
            return {
                "result": "success",
                "service": service,
                "target": target_device,
                "message": success_msg,
            }
        except asyncio.TimeoutError:
            error_msg = f"Timeout calling service {service} (took more than 5 seconds)"
            _LOGGER.error("❌ %s", error_msg)
            print(f"\n{'='*80}")
            print(f"TOOL TIMEOUT: {error_msg}")
            print(f"{'='*80}\n")
            return {
                "result": "error",
                "error": error_msg,
            }
        except Exception as err:
            error_msg = f"Error calling service {service}: {err}"
            _LOGGER.error("❌ %s", error_msg, exc_info=True)
            print(f"\n{'='*80}")
            print(f"TOOL ERROR: {error_msg}")
            print(f"{'='*80}\n")
            return {
                "result": "error",
                "error": error_msg,
            }


class BedrockServicesAPI(llm.API):
    """Bedrock Services LLM API."""

    def __init__(self, hass: HomeAssistant, id: str, name: str) -> None:
        """Initialize the API."""
        self.hass = hass
        self.id = id
        self.name = name

    async def async_get_api_instance(
        self, llm_context: llm.LLMContext
    ) -> llm.APIInstance:
        """Get API instance."""
        tools = [HassServiceTool(self.hass)]
        
        return llm.APIInstance(
            api=self,
            api_prompt=(
                "You have access to the HassCallService tool to control Home Assistant devices. "
                "CRITICAL: The device list in the system prompt contains all available devices with their entity_ids. "
                "When the user asks to control a device, YOU MUST: "
                "1. Search the device list for a matching entity based on the user's natural language (e.g., 'lamp', 'bedroom light') "
                "2. Identify the correct entity_id from that list "
                "3. Call HassCallService with the exact entity_id you found "
                "NEVER ask the user for an entity_id - always find it yourself from the provided device list."
            ),
            llm_context=llm_context,
            tools=tools,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AWS Bedrock Conversation from a config entry."""
    # Use ERROR level to ensure visibility
    _LOGGER.error("🚀 BEDROCK SETUP: Starting integration setup")
    print("\n" + "="*80)
    print("BEDROCK INTEGRATION SETUP STARTING")
    print("="*80 + "\n")
    
    # Register the LLM API if not already registered
    existing_apis = [api.id for api in llm.async_get_apis(hass)]
    if HOME_LLM_API_ID not in existing_apis:
        llm.async_register_api(hass, BedrockServicesAPI(hass, HOME_LLM_API_ID, "AWS Bedrock Services"))
        _LOGGER.error("✅ BEDROCK SETUP: Registered Bedrock Services LLM API")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    # Create the Bedrock client and store it in the entry's runtime_data
    entry.runtime_data = {}
    entry.runtime_data["client"] = BedrockClient(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.error("✅ BEDROCK SETUP: Integration setup complete")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.error("🔄 BEDROCK UNLOAD: Unloading integration")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unload_ok

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.error("🔄 BEDROCK RELOAD: Reloading due to configuration change")
    await hass.config_entries.async_reload(entry.entry_id)
