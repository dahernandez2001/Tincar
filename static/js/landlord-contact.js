/**
 * Sistema de Menú Lateral de Contacto del Arrendador
 * Para que el conductor pueda ver información del arrendador durante la reserva
 */

/**
 * Abre el menú lateral con información del arrendador
 * @param {number} ownerId - ID del arrendador
 * @param {string} parkingName - Nombre del garaje
 */
function openLandlordContactMenu(ownerId, parkingName) {
    // Obtener información del arrendador
    fetch(`/api/users/profile/${ownerId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const landlord = data.user;
                showLandlordContactMenu(landlord, parkingName);
            } else {
                alert('No se pudo cargar la información del arrendador');
            }
        })
        .catch(error => {
            console.error('Error cargando info del arrendador:', error);
            alert('Error de conexión');
        });
}

/**
 * Muestra el menú lateral con la información del arrendador
 */
function showLandlordContactMenu(landlord, parkingName) {
    const menuHTML = `
        <aside id="landlordContactMenu" class="account-side-menu active" style="z-index: 10001;">
            <div class="account-menu-header">
                <h3>Información de Contacto</h3>
                <button class="close-account-menu" onclick="closeLandlordContactMenu()">×</button>
            </div>
            <div class="account-menu-body">
                <div class="account-info">
                    <div class="profile-circle-large mx-auto mb-3" style="
                        background-image: url('${landlord.profile_photo || '/static/img/cono.png'}');
                        background-size: cover;
                        background-position: center;
                    "></div>
                    <h4 class="text-center mb-2">${landlord.name || 'Arrendador'}</h4>
                    <p class="text-center text-warning mb-3">
                        <i class="fas fa-warehouse"></i> ${parkingName}
                    </p>
                </div>
                <hr class="my-3" style="border-color: #FFB300;">
                <div class="contact-details">
                    <div class="contact-item mb-3">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-envelope text-warning me-3" style="font-size: 20px;"></i>
                            <div>
                                <small class="text-secondary d-block">Correo</small>
                                <span class="text-light">${landlord.email || 'No disponible'}</span>
                            </div>
                        </div>
                    </div>
                    <div class="contact-item mb-3">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-phone text-warning me-3" style="font-size: 20px;"></i>
                            <div>
                                <small class="text-secondary d-block">Teléfono</small>
                                <span class="text-light">${landlord.phone || 'No disponible'}</span>
                            </div>
                        </div>
                    </div>
                    <div class="contact-item mb-3">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-star text-warning me-3" style="font-size: 20px;"></i>
                            <div>
                                <small class="text-secondary d-block">Calificación</small>
                                <span class="text-warning">${landlord.rating ? landlord.rating.toFixed(1) : '0.0'} ⭐</span>
                            </div>
                        </div>
                    </div>
                </div>
                <hr class="my-3" style="border-color: #FFB300;">
                <div class="text-center">
                    <button class="btn btn-outline-light w-100" onclick="closeLandlordContactMenu()">
                        Cerrar
                    </button>
                </div>
            </div>
        </aside>
        <div id="landlordContactOverlay" class="account-menu-overlay active" onclick="closeLandlordContactMenu()"></div>
    `;
    
    // Insertar el menú en el body
    document.body.insertAdjacentHTML('beforeend', menuHTML);
    
    // Mover el cono de notificaciones
    const notificationCone = document.getElementById('notificationIcon');
    if (notificationCone) {
        notificationCone.classList.add('with-landlord-menu');
    }
}

/**
 * Cierra el menú lateral de contacto del arrendador
 */
function closeLandlordContactMenu() {
    const menu = document.getElementById('landlordContactMenu');
    const overlay = document.getElementById('landlordContactOverlay');
    
    if (menu) menu.remove();
    if (overlay) overlay.remove();
    
    // Restaurar posición del cono
    const notificationCone = document.getElementById('notificationIcon');
    if (notificationCone) {
        notificationCone.classList.remove('with-landlord-menu');
    }
}
