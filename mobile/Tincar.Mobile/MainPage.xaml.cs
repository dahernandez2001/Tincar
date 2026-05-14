using System.Collections.ObjectModel;
using Tincar.Mobile.Models;
using Tincar.Mobile.Services;

namespace Tincar.Mobile;

public partial class MainPage : ContentPage
{
	private readonly ITincarApiClient _apiClient;
	private readonly ObservableCollection<ParkingViewModel> _parkings = [];

	public MainPage(ITincarApiClient apiClient)
	{
		_apiClient = apiClient;
		InitializeComponent();
		ParkingsCollection.ItemsSource = _parkings;
	}

	private async void OnLoadParkingsClicked(object? sender, EventArgs e)
	{
		var baseUrl = BaseUrlEntry.Text?.Trim();
		if (string.IsNullOrWhiteSpace(baseUrl))
		{
			StatusLabel.Text = "Ingresa la URL base del backend.";
			return;
		}

		StatusLabel.Text = "Consultando API...";
		try
		{
			await _apiClient.SetBaseUrlAsync(baseUrl);
			var parkings = await _apiClient.GetActiveParkingsAsync();
			_parkings.Clear();
			foreach (var p in parkings)
			{
				_parkings.Add(new ParkingViewModel
				{
					Name = p.Name ?? "Sin nombre",
					Address = p.Address ?? "Sin dirección",
					CityLine = $"{p.City ?? "Ciudad N/D"} - {p.Department ?? "Depto N/D"}",
					Status = p.Status ?? "Libre"
				});
			}

			StatusLabel.Text = $"Parqueaderos cargados: {_parkings.Count}";
		}
		catch (Exception ex)
		{
			StatusLabel.Text = $"Error al consultar API: {ex.Message}";
		}
	}
}

public sealed class ParkingViewModel
{
	public string Name { get; init; } = string.Empty;
	public string Address { get; init; } = string.Empty;
	public string CityLine { get; init; } = string.Empty;
	public string Status { get; init; } = string.Empty;
}
