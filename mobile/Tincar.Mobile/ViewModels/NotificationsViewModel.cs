using System.Collections.ObjectModel;
using System.Windows.Input;
using Tincar.Mobile.Models;
using Tincar.Mobile.Services;

namespace Tincar.Mobile.ViewModels;

public sealed class NotificationsViewModel : BaseViewModel
{
    private readonly ITincarApiClient _apiClient;

    public NotificationsViewModel(ITincarApiClient apiClient)
    {
        _apiClient = apiClient;
        LoadCommand = new Command(async () => await LoadAsync(), () => !IsBusy);
    }

    public ObservableCollection<NotificationItem> Notifications { get; } = [];

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
            StatusMessage = "Cargando notificaciones...";
            var items = await _apiClient.GetNotificationsAsync();
            Notifications.Clear();
            foreach (var item in items)
            {
                Notifications.Add(item);
            }

            StatusMessage = $"Notificaciones: {Notifications.Count}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"No se pudieron cargar notificaciones: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }
}
