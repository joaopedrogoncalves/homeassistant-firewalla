# Firewalla Integration for Home Assistant

This custom component integrates your Firewalla device(s) with Home Assistant, allowing you to monitor the status and statistics of your Firewalla.

## Features

- Monitor online status of your Firewalla
- Track the number of devices connected to your network
- Monitor rule count
- Track alarm count
- View device information like model, version, mode, etc.

## Installation

### HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS:
   - Click on HACS in the sidebar
   - Click on "Integrations"
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL: `https://github.com/joaopedrogoncalves/homeassistant-firewalla`
   - Select "Integration" as the category
   - Click "Add"
3. Search for "Firewalla" in HACS integrations
4. Click "Install"
5. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [GitHub repository](https://github.com/joaopedrogoncalves/homeassistant-firewalla)
2. Extract the contents to your Home Assistant config directory under `custom_components/firewalla`
3. Restart Home Assistant

## Configuration

1. Go to **Settings** -> **Devices & Services**
2. Click the **+ Add Integration** button
3. Search for "Firewalla" and select it
4. Enter your Firewalla MSP domain (e.g., `api.firewalla.com`)
5. Enter your Firewalla API token
6. Click "Submit"

## Obtaining Your API Token

1. Log in to your Firewalla MSP account
2. Go to your account settings
3. Generate or copy your personal access token
4. Make sure the token has read permissions for your devices

## Entities Created

For each Firewalla device, the following entities will be created:

- **Binary Sensor**:
  - `binary_sensor.firewalla_online`: Indicates if the Firewalla is online

- **Sensors**:
  - `sensor.firewalla_device_count`: Number of devices connected to your network
  - `sensor.firewalla_rule_count`: Number of rules configured on your Firewalla
  - `sensor.firewalla_alarm_count`: Number of current alarms

## Troubleshooting

### Connection Issues

- Verify that your Firewalla MSP domain is correct
- Verify that your API token is valid and has not expired
- Check if your Firewalla device is online and connected to the internet

### Logs

To get more detailed information for troubleshooting, you can enable debug logging for the component:

```yaml
logger:
  default: info
  logs:
    custom_components.firewalla: debug
```

## Support

If you encounter any issues or have questions, please:

1. Check the [GitHub Issues](https://github.com/joaopedrogoncalves/homeassistant-firewalla/issues) to see if your issue has been reported
2. If not, create a new issue with detailed information about the problem

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
