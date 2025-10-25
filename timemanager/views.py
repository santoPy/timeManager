from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import json
from django.utils import timezone
import pytz


def index(request):
    """Render the main page"""
    return render(request, 'index.html')


@csrf_exempt
def calculate_time(request):
    """Process attendance data and return calculated results"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            attendance_text = data.get('attendance_data', '')
            total_working_hours = float(data.get('working_hours', 8))

            # Parse the tab-separated data
            lines = attendance_text.strip().split('\n')
            if len(lines) < 2:
                return JsonResponse({'error': 'Invalid data format'}, status=400)

            # Parse headers
            headers = [h.strip() for h in lines[0].split('\t')]

            # Parse rows
            all_rows = []
            for line in lines[1:]:
                columns = line.strip().split('\t')
                if len(columns) != len(headers):
                    continue

                row = {}
                for header, value in zip(headers, columns):
                    cleaned_value = ' '.join(value.strip().split())
                    row[header] = cleaned_value
                all_rows.append(row)

            if not all_rows:
                return JsonResponse({'error': 'No valid data found'}, status=400)

            # Employee info
            first_row = all_rows[0]
            employee_code = first_row.get('Employee Code', 'N/A')
            employee_name = first_row.get('Employee Name', 'N/A')
            date = first_row.get("Event Date", "").split()[0]
            in_time = first_row.get("Event Date", "").split()[1] if len(first_row.get("Event Date", "").split()) > 1 else "N/A"

            # Convert Event Date to datetime objects
            ist = pytz.timezone('Asia/Kolkata')
            for row in all_rows:
                try:
                    naive_dt = datetime.strptime(row["Event Date"], "%d-%m-%Y %H:%M:%S")
                    row["Event Date"] = ist.localize(naive_dt)  # Make timezone-aware
                except ValueError:
                    continue

            # Process punch records
            first_in_time = all_rows[0]["Event Date"]
            working_duration = timedelta(hours=total_working_hours)
            last_out_time = None
            currently_logged_in = False

            pairs = []
            waiting_out = None
            break_time = timedelta(0)
            expected_out_time = first_in_time + working_duration

            processing_log = []

            for row in all_rows:
                desc = row["Description"].upper()
                event_time = row["Event Date"]

                if "OUT" in desc:
                    waiting_out = row
                elif "IN" in desc and waiting_out:
                    out_time = waiting_out["Event Date"]
                    in_time_event = event_time

                    temp_expected_out = first_in_time + working_duration + break_time

                    if out_time >= temp_expected_out:
                        processing_log.append({
                            'type': 'ignored',
                            'message': f"OUT at {out_time.strftime('%I:%M:%S %p')} is >= expected logout {temp_expected_out.strftime('%I:%M:%S %p')}"
                        })
                        waiting_out = None
                        continue

                    capped = False
                    if in_time_event > temp_expected_out:
                        delta = temp_expected_out - out_time
                        processing_log.append({
                            'type': 'capped',
                            'message': f"IN event at {in_time_event.strftime('%I:%M:%S %p')} - CAPPED to expected logout. Break duration capped from {(in_time_event - out_time)} to {delta}"
                        })
                        capped = True
                    else:
                        delta = in_time_event - out_time

                    pairs.append({
                        "out_desc": waiting_out["Description"],
                        "out_time": out_time.strftime('%I:%M:%S %p'),
                        "in_desc": row["Description"],
                        "in_time": in_time_event.strftime('%I:%M:%S %p'),
                        "duration": str(delta),
                        "capped": capped
                    })

                    break_time += delta
                    expected_out_time = first_in_time + working_duration + break_time
                    waiting_out = None

            # Find last OUT event
            for row in reversed(all_rows):
                desc = row["Description"].upper()
                if "OUT" in desc:
                    last_out_time = row["Event Date"]
                    currently_logged_in = False
                    break
                elif "IN" in desc:
                    currently_logged_in = True
                    break

            # Calculate working hours
            result = {
                'employee_code': employee_code,
                'employee_name': employee_name,
                'date': date,
                'in_time': in_time,
                'first_in_time': first_in_time.strftime('%I:%M:%S %p'),
                'required_hours': total_working_hours,
                'pairs': pairs,
                'processing_log': processing_log,
                'break_time': str(break_time),
                'expected_out_time': expected_out_time.strftime('%I:%M:%S %p'),
                'currently_logged_in': currently_logged_in
            }

            if last_out_time:
                total_time = last_out_time - first_in_time
                actual_working_time = total_time - break_time
                total_minutes = int(actual_working_time.total_seconds() / 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60

                result['you_worked'] = f"{hours}:{minutes:02d} hrs"
                result['you_worked_detail'] = str(actual_working_time)

                required_minutes = int(total_working_hours * 60)
                if total_minutes > required_minutes:
                    extra_minutes = total_minutes - required_minutes
                    extra_hours = extra_minutes // 60
                    extra_mins = extra_minutes % 60
                    result['status'] = 'overtime'
                    result['extra_hours'] = f"+{extra_hours}:{extra_mins:02d} hrs"
                elif total_minutes < required_minutes:
                    deficit_minutes = required_minutes - total_minutes
                    deficit_hours = deficit_minutes // 60
                    deficit_mins = deficit_minutes % 60
                    result['status'] = 'incomplete'
                    result['short_by'] = f"-{deficit_hours}:{deficit_mins:02d} hrs"
                    result['pending_hours'] = f"{deficit_hours}:{deficit_mins:02d} hrs"
                else:
                    result['status'] = 'complete'

                result['actual_out_time'] = last_out_time.strftime('%I:%M:%S %p')

                if last_out_time > expected_out_time:
                    overtime = last_out_time - expected_out_time
                    ot_minutes = int(overtime.total_seconds() / 60)
                    ot_hours = ot_minutes // 60
                    ot_mins = ot_minutes % 60
                    result['overtime_indicator'] = f"+{ot_hours}:{ot_mins:02d} hrs"

            elif currently_logged_in:
                current_time = timezone.localtime()
                total_time = current_time - first_in_time
                actual_working_time = total_time - break_time
                total_minutes = int(actual_working_time.total_seconds() / 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60

                result['status'] = 'logged_in'
                result['you_worked_so_far'] = f"{hours}:{minutes:02d} hrs"

                required_minutes = int(total_working_hours * 60)
                if total_minutes < required_minutes:
                    remaining_minutes = required_minutes - total_minutes
                    remaining_hours = remaining_minutes // 60
                    remaining_mins = remaining_minutes % 60
                    result['pending_hours'] = f"{remaining_hours}:{remaining_mins:02d} hrs"

                    expected_logout_now = current_time + timedelta(minutes=remaining_minutes)
                    result['complete_shift_by'] = expected_logout_now.strftime('%I:%M:%S %p')

            return JsonResponse({'success': True, 'result': result})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
from django.shortcuts import render

# Create your views here.
