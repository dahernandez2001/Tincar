using Microsoft.Extensions.Logging;
using Tincar.Mobile.Pages;
using Tincar.Mobile.Services;
using Tincar.Mobile.ViewModels;

namespace Tincar.Mobile;

public static class MauiProgram
{
	public static MauiApp CreateMauiApp()
	{
		var builder = MauiApp.CreateBuilder();
		builder
			.UseMauiApp<App>()
			.ConfigureFonts(fonts =>
			{
				fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
				fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
			});

		builder.Services.AddSingleton<IEnvironmentConfigService, EnvironmentConfigService>();
		builder.Services.AddSingleton<ITincarApiClient, TincarApiClient>();
		builder.Services.AddSingleton<AppShell>();

		builder.Services.AddTransient<LoginViewModel>();
		builder.Services.AddTransient<ParkingsViewModel>();
		builder.Services.AddTransient<ReservationsViewModel>();
		builder.Services.AddTransient<NotificationsViewModel>();

		builder.Services.AddTransient<LoginPage>();
		builder.Services.AddTransient<ParkingsPage>();
		builder.Services.AddTransient<ReservationsPage>();
		builder.Services.AddTransient<NotificationsPage>();

#if DEBUG
		builder.Logging.AddDebug();
#endif

		return builder.Build();
	}
}
