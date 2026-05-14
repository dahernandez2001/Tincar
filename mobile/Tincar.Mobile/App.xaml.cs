using Microsoft.Extensions.DependencyInjection;

namespace Tincar.Mobile;

public partial class App : Application
{
	public App()
	{
		InitializeComponent();
	}

	protected override Window CreateWindow(IActivationState? activationState)
	{
		var shell = IPlatformApplication.Current?.Services.GetRequiredService<AppShell>()
			?? throw new InvalidOperationException("No se pudo resolver AppShell desde DI.");
		return new Window(shell);
	}
}