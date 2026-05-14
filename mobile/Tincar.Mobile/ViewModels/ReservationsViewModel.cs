using System.Collections.ObjectModel;
using System.Windows.Input;
using Tincar.Mobile.Models;
using Tincar.Mobile.Services;

namespace Tincar.Mobile.ViewModels;

public sealed class ReservationsViewModel : BaseViewModel
{
    private readonly ITincarApiClient _apiClient;

    public ReservationsViewModel(ITincarApiClient apiClient)
    {
        _apiClient = apiClient;
        LoadCommand = new Command(async () => await LoadAsync(), () => !IsBusy);
    }

    public ObservableCollection<DriverReservation> Reservations { get; } = [];

    public ICommand LoadCommand { get; }

    public async Task LoadAsync()
    {
        if (IsBusy)
        {
            return;
        }

        try
        {
            IsBusy = true;
            StatusMessage = "Cargando reservas activas...";
            var items = await _apiClient.GetActiveDriverReservationsAsync();
            Reservations.Clear();
            foreach (var item in items)
            {
                Reservations.Add(item);
            }

            StatusMessage = $"Reservas activas: {Reservations.Count}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"No se pudieron cargar reservas: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }
}
