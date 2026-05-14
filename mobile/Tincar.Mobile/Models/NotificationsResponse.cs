namespace Tincar.Mobile.Models;

public sealed class NotificationsResponse
{
    public bool Success { get; set; }
    public List<NotificationItem>? Notifications { get; set; }
    public string? Error { get; set; }
}
