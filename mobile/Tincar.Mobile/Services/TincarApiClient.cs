using System.Text.Json;
using Tincar.Mobile.Models;

namespace Tincar.Mobile.Services;

public sealed class TincarApiClient : ITincarApiClient
{
    private readonly IEnvironmentConfigService _environmentConfigService;
    private readonly HttpClient _httpClient;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public TincarApiClient(IEnvironmentConfigService environmentConfigService)
    {
        _environmentConfigService = environmentConfigService;
        var handler = new HttpClientHandler
        {
            UseCookies = true,
            CookieContainer = new CookieContainer(),
            AllowAutoRedirect = true
        };
        _httpClient = new HttpClient(handler);
    }

    public async Task<string> GetBaseUrlAsync()
    {
        var baseUrl = await _environmentConfigService.GetBaseUrlAsync();
        _httpClient.BaseAddress = new Uri(baseUrl);
        return baseUrl;
    }

    public async Task SetBaseUrlAsync(string baseUrl)
    {
        await _environmentConfigService.SetBaseUrlAsync(baseUrl);
        _httpClient.BaseAddress = new Uri(await _environmentConfigService.GetBaseUrlAsync());
    }

    public async Task<AuthResult> LoginAsync(string email, string password, CancellationToken cancellationToken = default)
    {
        await EnsureBaseAddressAsync();

        var content = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["email"] = email,
            ["password"] = password
        });

        using var response = await _httpClient.PostAsync("/login", content, cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            return new AuthResult
            {
                Success = false,
                Message = $"Login fallido: HTTP {(int)response.StatusCode}"
            };
        }

        var authenticated = await IsAuthenticatedAsync(cancellationToken);
        return new AuthResult
        {
            Success = authenticated,
            Message = authenticated ? "Sesión iniciada" : "Credenciales inválidas o sesión no creada"
        };
    }

    public async Task LogoutAsync(CancellationToken cancellationToken = default)
    {
        await EnsureBaseAddressAsync();
        using var _ = await _httpClient.GetAsync("/logout", cancellationToken);
    }

    public async Task<bool> IsAuthenticatedAsync(CancellationToken cancellationToken = default)
    {
        await EnsureBaseAddressAsync();
        using var response = await _httpClient.GetAsync("/api/users/profile", cancellationToken);
        return response.IsSuccessStatusCode;
    }

    public async Task<IReadOnlyList<Parking>> GetActiveParkingsAsync(CancellationToken cancellationToken = default)
    {
        await EnsureBaseAddressAsync();
        var data = await ReadJsonAsync<ActiveParkingsResponse>("/api/parkings/active", cancellationToken);
        if (!data.Success)
        {
            throw new InvalidOperationException(data.Error ?? "La API devolvió un error al cargar parkings.");
        }

        return data.Parkings ?? [];
    }

    public async Task<IReadOnlyList<NotificationItem>> GetNotificationsAsync(CancellationToken cancellationToken = default)
    {
        await EnsureBaseAddressAsync();
        var data = await ReadJsonAsync<NotificationsResponse>("/api/notifications", cancellationToken);
        if (!data.Success)
        {
            throw new InvalidOperationException(data.Error ?? "La API devolvió un error al cargar notificaciones.");
        }

        return data.Notifications ?? [];
    }

    public async Task<IReadOnlyList<DriverReservation>> GetActiveDriverReservationsAsync(CancellationToken cancellationToken = default)
    {
        await EnsureBaseAddressAsync();
        var data = await ReadJsonAsync<ActiveDriverReservationsResponse>("/api/reservations/active/driver", cancellationToken);
        if (!data.Success)
        {
            throw new InvalidOperationException(data.Error ?? "La API devolvió un error al cargar reservas.");
        }

        return data.Reservations ?? [];
    }

    private async Task EnsureBaseAddressAsync()
    {
        if (_httpClient.BaseAddress is null)
        {
            _httpClient.BaseAddress = new Uri(await _environmentConfigService.GetBaseUrlAsync());
        }
    }

    private async Task<T> ReadJsonAsync<T>(string endpoint, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync(endpoint, cancellationToken);
        var payload = await response.Content.ReadAsStringAsync(cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException($"HTTP {(int)response.StatusCode}: {payload}");
        }

        var data = JsonSerializer.Deserialize<T>(payload, JsonOptions);
        if (data is null)
        {
            throw new InvalidOperationException("No se pudo parsear la respuesta de la API.");
        }

        return data;
    }
}
