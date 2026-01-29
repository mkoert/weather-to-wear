## If its 2025-12-14 19:40, only return hours from 2025-12-14 20:00 to 2025-12-15 19:00
def get_hourly_data(data, current_date):
        """Extract hourly data from Visual Crossing API response"""
        from datetime import datetime, timezone, timedelta

        hourly_list = []

        # Get timezone offset from API response
        tzoffset = data.get('tzoffset', 0)
        tz = timezone(timedelta(hours=tzoffset))

        # Get current datetime in the API's timezone (round down to the hour)
        current_datetime = datetime.now(tz).replace(minute=0, second=0, microsecond=0)

        # print("Extracting hourly data...")
        # print(f"Timezone: {data.get('timezone')} (offset: {tzoffset})")
        # print(f"Current datetime (rounded to hour): {current_datetime}")
        # Visual Crossing returns days array
        if 'days' in data and isinstance(data['days'], list):
            for day in data['days']:
                day_date = day.get('datetime')
                if 'hours' in day and isinstance(day['hours'], list):
                    for hour in day['hours']:
                        hour_time = hour.get('datetime')
                        # print(f"Processing hour: day_date={day_date}, hour_time={hour_time}")

                        # Combine day_date and hour_time into a full datetime for comparison
                        if day_date and hour_time:
                            full_datetime = datetime.strptime(f"{day_date} {hour_time}", "%Y-%m-%d %H:%M:%S")
                            # Make it timezone-aware using the API's timezone
                            full_datetime = full_datetime.replace(tzinfo=tz)

                            # Skip hours up to and including current datetime
                            if full_datetime <= current_datetime:
                                print(f"Skipping past hour: {full_datetime}")
                                continue


                        # Stop once we have 24 hours
                        if len(hourly_list) >= 24:
                            break

                        # print(f"Adding hour: day_date={day_date}, hour_time={hour_time}")
                        hourly_list.append({
                            'datetime': hour.get('datetime'),
                            'temp': hour.get('temp'),
                            'humidity': hour.get('humidity'),
                            'conditions': hour.get('conditions'),
                            'windspeed': hour.get('windspeed'),
                            'precip': hour.get('precip')
                        })
                if len(hourly_list) >= 24:
                    break

        return hourly_list

