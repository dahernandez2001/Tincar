using System.Text.Json.Serialization;

namespace Tincar.Mobile.Models;

public sealed class NotificationItem
{
    public int Id { get; set; }
    public string? Message { get; set; }
    public string? Type { get; set; }
    public string? Status { get; set; }

    [JsonPropertyName("created_at")]
    public string? CreatedAt { get; set; }
}
