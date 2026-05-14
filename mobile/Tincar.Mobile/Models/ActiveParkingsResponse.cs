namespace Tincar.Mobile.Models;

public sealed class ActiveParkingsResponse
{
    public bool Success { get; set; }
    public List<Parking>? Parkings { get; set; }
    public string? Error { get; set; }
}
