1. integrate with google calendar
2. fix time description in add tool, for example:

```
hi, put a reminder for me to get the trash out in the next 30min
Centi

Inspect
Just a moment.
Your reminder to take out the trash in 30 minutes is set.
```

in the database was saved as:

```
[{'id': 2, 'time': '30 minutes from now', 'description': 'Take out the trash', 'created_at': '2025-11-12T13:51:54.814263+00:00', 'updated_at': None}] count=None
```

should be 30min + now()