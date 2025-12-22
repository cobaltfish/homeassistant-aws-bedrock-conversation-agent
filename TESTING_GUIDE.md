# Testing the Light Control Fix

## Quick Test Procedure

### 1. Restart Home Assistant
After updating the code, restart Home Assistant to load the new version:
```bash
# If running in Docker
docker restart homeassistant

# If running as a service
sudo systemctl restart home-assistant@homeassistant.service

# Or restart from the UI
Settings → System → Restart
```

### 2. Enable Debug Logging (Optional but Recommended)

Edit `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.bedrock_conversation: debug
```

Restart Home Assistant again after making this change.

### 3. Test Device Control

Try these commands with your conversation agent:

✅ **Basic Light Control**
- "Turn on the kitchen light"
- "Turn off the bedroom light"
- "Dim the living room light to 50%"
- "Set the hallway light to red"

✅ **Other Device Types**
- "Turn on the fan"
- "Set thermostat to 72 degrees"
- "Close the garage door"

✅ **Non-Device Queries (should still work)**
- "What lights do I have?"
- "What's the temperature in the bedroom?"
- "Tell me about my devices"

### 4. Expected Behavior

**Before the fix:**
- UI shows "..." spinning indefinitely
- No response ever comes back
- Light may or may not turn on
- Have to reload the page to stop the spinning

**After the fix:**
- UI shows "..." for 1-3 seconds
- Response appears with confirmation message
- Light turns on/off as expected
- Can immediately ask another question

### 5. Check Logs

If you enabled debug logging, check `home-assistant.log`:

```bash
tail -f /config/home-assistant.log | grep bedrock_conversation
```

**Success indicators:**
```
DEBUG: Found tool use 'HassCallService' with ID: toolu_01ABC123
DEBUG: Executing tool: HassCallService with args: {'service': 'light.turn_on', ...}
DEBUG: Tool HassCallService completed with result: {'result': 'success', ...} (using ID: toolu_01ABC123)
DEBUG: Bedrock response - stop_reason: end_turn, content_blocks: 1
```

**Problem indicators:**
```
ERROR: Error calling Bedrock: ...
ERROR: Timeout waiting for response
WARNING: Max iterations reached
```

### 6. Verify Configuration

Settings → Devices & Services → AWS Bedrock Conversation → Configure

Ensure:
- ✅ **LLM API** is set to "AWS Bedrock Services"
- ✅ **Max Tool Call Iterations** is at least 10
- ✅ A valid Claude model is selected (e.g., claude-3-5-sonnet)
- ✅ AWS credentials are valid

### 7. Test Edge Cases

Once basic control works, try:

**Multiple devices:**
- "Turn on all the lights"
- "Turn off the bedroom light and turn on the kitchen light"

**Complex commands:**
- "Dim the living room light to 20% and set it to blue"
- "Turn on the fan and set it to medium speed"

**Error cases:**
- "Turn on the nonexistent light" (should get error message, not spin)
- "Set the light to 999%" (should handle gracefully)

## Troubleshooting

### Still Spinning?

1. **Check entity exposure**: 
   - Go to Settings → Voice assistants → Expose tab
   - Make sure the lights you're trying to control are checked

2. **Verify AWS credentials**:
   ```bash
   aws bedrock list-foundation-models --region YOUR_REGION
   ```

3. **Check Bedrock model access**:
   - Ensure you have access to the selected Claude model
   - Try switching to a different model (e.g., claude-3-haiku)

4. **Look for errors in logs**:
   ```bash
   grep -i error /config/home-assistant.log | grep bedrock
   ```

### Works But Response is Slow?

- This is normal for Bedrock API calls (1-3 seconds)
- Consider using a faster model like claude-3-haiku
- Check your AWS region latency

### Gets Wrong Device?

The LLM is doing fuzzy matching on device names. If it picks the wrong one:
- Make device names more distinct (rename in Home Assistant)
- Be more specific in your command ("kitchen ceiling light" vs. "kitchen light")
- Check the system prompt to see what names the LLM sees

### Tool Call Fails?

Check the error message. Common issues:
- **"Service domain not allowed"**: The service isn't in the allowlist (modify `const.py`)
- **"Entity not found"**: The device isn't exposed or doesn't exist
- **"Permission denied"**: Home Assistant user permissions issue

## Success Criteria

✅ Lights turn on/off when requested  
✅ Response comes back within 3 seconds  
✅ UI shows confirmation message  
✅ No infinite spinning  
✅ Can chain multiple commands in a conversation  
✅ Error messages are displayed properly (not infinite spin)  

## Reporting Issues

If the fix doesn't work:

1. Capture logs with debug enabled
2. Note the exact command that fails
3. Check `FIX_SUMMARY.md` for known issues
4. Open a GitHub issue with:
   - Home Assistant version
   - Integration version
   - Claude model being used
   - Debug logs showing the failure
   - Expected vs. actual behavior

## Performance Benchmarks

Expected response times with claude-3-5-sonnet:

| Query Type | Time |
|------------|------|
| Non-device query | 1-2s |
| Single device control | 2-3s |
| Multiple device control | 3-5s |
| Complex with attributes | 3-5s |

Times will vary based on:
- AWS region proximity
- Selected Claude model
- Current API load
- System prompt complexity
