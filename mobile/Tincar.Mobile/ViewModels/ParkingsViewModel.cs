using System.Collections.ObjectModel;
using System.Windows.Input;
using Tincar.Mobile.Models;
using Tincar.Mobile.Services;

namespace Tincar.Mobile.ViewModels;

public sealed class ParkingsViewModel : BaseViewModel
{
    private readonly ITincarApiClient _apiClient;

    public ParkingsViewModel(ITincarApiClient apiClient)
    {
        _apiClient = apiClient;
        LoadCommand = new Command(async () => await LoadAsync(), () => !IsBusy);
    }

    public ObservableCollection<Parking> Parkings { get; } = [];

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
            StatusMessage = "Cargando parqueaderos activos...";
            var items = await _apiClient.GetActiveParkingsAsync();
            Parkings.Clear();
            foreach (var item in items)
            {
                Parkings.Add(item);
            }

            StatusMessage = $"Parqueaderos encontrados: {Parkings.Count}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"No se pudieron cargar parkings: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }
}
