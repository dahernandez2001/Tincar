namespace Tincar.Mobile.Models;

public sealed class ActiveDriverReservationsResponse
{
    public bool Success { get; set; }
    public List<DriverReservation>? Reservations { get; set; }
    public string? Error { get; set; }
}
