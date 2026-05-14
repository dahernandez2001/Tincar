using Tincar.Mobile.Pages;

namespace Tincar.Mobile;

public partial class AppShell : Shell
{
	public AppShell(
		LoginPage loginPage,
		ParkingsPage parkingsPage,
		ReservationsPage reservationsPage,
		NotificationsPage notificationsPage)
	{
		InitializeComponent();

		var tabBar = new TabBar();
		tabBar.Items.Add(new ShellContent { Title = "Login", Content = loginPage, Route = nameof(LoginPage) });
		tabBar.Items.Add(new ShellContent { Title = "Parkings", Content = parkingsPage, Route = nameof(ParkingsPage) });
		tabBar.Items.Add(new ShellContent { Title = "Reservas", Content = reservationsPage, Route = nameof(ReservationsPage) });
		tabBar.Items.Add(new ShellContent { Title = "Notificaciones", Content = notificationsPage, Route = nameof(NotificationsPage) });

		Items.Add(tabBar);
	}
}
