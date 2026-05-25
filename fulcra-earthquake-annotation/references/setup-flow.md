# Setup Flow

Use this when creating or changing a Fulcra earthquake monitor. Keep every numbered choice open to free-form write-in text.

## 1. Intro

```text
I'll set up Fulcra earthquake annotations using the USGS earthquake feed.

I'll use your Fulcra location context to suggest a monitoring area.
```

## 2. Monitoring Area

Infer the current town/city and a sensible wider region from Fulcra context. Keep the list narrow:

```text
Based on your current Fulcra location, what area should I monitor?

1. Nearby - 100 mi around {town/city}
2. Wider region - 250 mi around {region}
3. Use a different address or place
4. Write in my own area/radius

Reply with a number, or write your own.
```

Examples:

```text
1. Nearby - 100 mi around Honalo, Hawaii
2. Wider region - 250 mi around Hawaii Island
```

```text
1. Nearby - 100 mi around Los Angeles, CA
2. Wider region - 250 mi around Southern California
```

If the user chooses a different address/place, geocode it, propose a radius, and ask for confirmation or a write-in radius.

## 3. Annotation/Data Type Name

```text
Suggested annotation name:

{Region} Earthquakes

Reply yes to use this, or write your own.
```

Examples: `BI Earthquakes`, `Big Island Earthquakes`, `Southern California Earthquakes`, `Nearby Earthquakes`.

## 4. Polling Frequency

```text
How often should I check USGS?

1. Every 30 minutes
2. Hourly - default
3. Every 3 hours
4. Every day

Reply with a number, or write your own. You can always ask your agent to check USGS manually anytime if you need it sooner.
```

Default: hourly.

## 5. Fulcra Recording Threshold

```text
Do you want me to record earthquakes of 4.0 and above in your Fulcra datastore?

Reply yes, no, or write a different minimum magnitude.
```

Interpretation:

- `yes` means record `M4.0+`.
- `no` means disable Fulcra recording.
- `4.5`, `M4.5+`, `only 5+`, etc. means enable recording with that threshold.
- Unclear response means ask one concise clarification.

## 6. Discord Notification Threshold

```text
Do you want Discord notifications for earthquakes of 5.0 and above?

Reply yes, no, or write a different minimum magnitude.
```

Interpretation:

- `yes` means notify for `M5.0+`.
- `no` means disable Discord notifications.
- Custom magnitude means notify with that threshold.

## 7. Discord Destination

Ask only if Discord notifications are enabled.

```text
Where should I send Discord notifications?

1. This Discord thread/channel
2. A different Discord channel
3. A Discord DM
4. Write in another destination

Reply with a number, or write your own.
```

Resolve named Discord destinations with available messaging target tools where possible. Do not guess opaque channel IDs.

## 8. Example Populated Fulcra Record

Before final confirmation, show a populated Fulcra record preview using the selected settings and either a recent USGS event or clearly labeled synthetic/example data.

```text
Here's an example of what I'd record:

{Annotation name}: {magnitude}

Tags:
{tags}

Note:
Time: {local time}
Magnitude: {magnitude}{, {max intensity} max intensity}
Epicenter: {distance + direction} of {nearest town/place}
My distance from epicenter: ~{distance} mi, {monitor location}
Tsunami watch: {yes/no/unknown}

USGS page: {event URL}
```

## 9. Final Confirmation

```text
Setup summary:
- Area: {area label}, {radius} mi
- Fulcra annotation: {name}
- Record to Fulcra: {record threshold or disabled}
- Discord notifications: {notify threshold or disabled}
- Check frequency: {poll interval}
- Notification destination: {destination or disabled}

Reply yes to create this, or tell me what to change.
```

Do not create the annotation definition, cron job, or Discord delivery until the user confirms this summary.
