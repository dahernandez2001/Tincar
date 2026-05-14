using Tincar.Mobile.Models;

namespace Tincar.Mobile.Services;

public interface ITincarApiClient
{
    Task<string> GetBaseUrlAsync();
    Task SetBaseUrlAsync(string baseUrl);
    Task<AuthResult> LoginAsync(string email, string password, CancellationToken cancellationToken = default);
    Task LogoutAsync(CancellationToken cancellationToken = default);
    Task<bool> IsAuthenticatedAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<Parking>> GetActiveParkingsAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<NotificationItem>> GetNotificationsAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<DriverReservation>> GetActiveDriverReservationsAsync(CancellationToken cancellationToken = default);
}
