using Tincar.Mobile.ViewModels;

namespace Tincar.Mobile.Pages;

public partial class ReservationsPage : ContentPage
{
    private readonly ReservationsViewModel _viewModel;

    public ReservationsPage(ReservationsViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        BindingContext = _viewModel;
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        await _viewModel.LoadAsync();
    }
}
