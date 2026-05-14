using System.Text.Json.Serialization;

namespace Tincar.Mobile.Models;

public sealed class DriverReservation
{
    public int Id { get; set; }
    public string? Status { get; set; }

    [JsonPropertyName("duration_minutes")]
    public int? DurationMinutes { get; set; }

    [JsonPropertyName("eta_minutes")]
    public int? EtaMinutes { get; set; }

    [JsonPropertyName("parking_name")]
    public string? ParkingName { get; set; }

    public string? Address { get; set; }

    [JsonPropertyName("created_at")]
    public string? CreatedAt { get; set; }
}
