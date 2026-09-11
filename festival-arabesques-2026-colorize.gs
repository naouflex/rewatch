/**
 * Apply per-event colors after importing festival-arabesques-2026.ics into Google Calendar.
 *
 * Google Calendar ignores color metadata in ICS files on import, so run this once
 * after importing the calendar file.
 *
 * Setup:
 * 1. Go to https://script.google.com/
 * 2. New project -> paste this file -> save
 * 3. Run colorizeFestivalArabesquesEvents() and authorize Calendar access
 */
function colorizeFestivalArabesquesEvents() {
  const calendar = CalendarApp.getDefaultCalendar();
  const start = new Date('2026-09-08T00:00:00');
  const end = new Date('2026-09-21T23:59:59');
  const events = calendar.getEvents(start, end);
  const colorIds = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'];
  let updated = 0;

  events.forEach(function (event) {
    const description = event.getDescription() || '';
    const match = description.match(/Google-Calendar-ColorId:\s*(\d{1,2})/);
    let colorId = match ? match[1] : null;

    if (!colorId) {
      colorId = colorIds[Math.floor(Math.random() * colorIds.length)];
    }

    event.setColor(colorId);
    updated++;
  });

  Logger.log('Colored ' + updated + ' Festival Arabesques events.');
}
