using Tincar.Mobile.ViewModels;

namespace Tincar.Mobile.Pages;

public partial class ParkingsPage : ContentPage
{
    private readonly ParkingsViewModel _viewModel;

    public ParkingsPage(ParkingsViewModel viewModel)
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
