// Subir foto de perfil
(function(){
  document.getElementById('profilePhotoInput')?.addEventListener('change', function(e) {
      const file = e.target.files[0];
      if (file) {
          uploadPhoto(file, 'profile', 'profilePhotoPreview');
      }
  });

  // Subir foto del documento
  document.getElementById('documentPhotoInput')?.addEventListener('change', function(e) {
      const file = e.target.files[0];
      if (file) {
          uploadPhoto(file, 'document', 'documentPhotoPreview');
      }
  });

  // Subir foto de la licencia
  document.getElementById('licensePhotoInput')?.addEventListener('change', function(e) {
      const file = e.target.files[0];
      if (file) {
          uploadPhoto(file, 'license', 'licensePhotoPreview');
      }
  });

  // Función para subir fotos
  function uploadPhoto(file, type, previewId) {
      const formData = new FormData();
      formData.append('photo', file);
      formData.append('type', type);
      
      // Mostrar preview inmediatamente
      const reader = new FileReader();
      reader.onload = function(e) {
          let preview = document.getElementById(previewId);
          if (!preview) {
              preview = document.createElement('img');
              preview.id = previewId;
              preview.className = 'preview-image';
              document.querySelector(`#${type}PhotoInput`).parentElement.appendChild(preview);
          }
          preview.src = e.target.result;
      };
      reader.readAsDataURL(file);
      
      // Subir archivo
      fetch('/api/driver/upload-photo', {
          method: 'POST',
          body: formData
      })
      .then(response => response.json())
      .then(data => {
          if (data.error) {
              alert('Error al subir la foto: ' + data.error);
          } else {
              alert('✅ Foto subida correctamente');
          }
      })
      .catch(error => {
          console.error('Error:', error);
          alert('Error al subir la foto');
      });
  }

  // Guardar cambios del formulario
  document.getElementById('profileForm')?.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const data = {};
      
      for (let [key, value] of formData.entries()) {
          if (value !== '') {
              data[key] = value;
          }
      }
      
      fetch('/api/driver/profile/{{ profile.id }}', {
          method: 'PUT',
          headers: {
              'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
      })
      .then(response => response.json())
      .then(data => {
          if (data.error) {
              alert('❌ Error: ' + data.error);
          } else {
              alert('✅ ' + data.message);
              location.reload();
          }
      })
      .catch(error => {
          console.error('Error:', error);
          alert('❌ Error al guardar los cambios');
      });
  });

  // Validar edad mínima al cambiar fecha de nacimiento
  document.querySelector('[name="birth_date"]')?.addEventListener('change', function() {
      const birthDate = new Date(this.value);
      const today = new Date();
      let age = today.getFullYear() - birthDate.getFullYear();
      const monthDiff = today.getMonth() - birthDate.getMonth();
      if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
        age--;
      }
      if (age < 18) {
          alert('⚠️ Debes tener al menos 18 años para ser conductor en TinCar');
          this.value = '';
      }
  });

  // Validar fecha de vencimiento de licencia
  document.querySelector('[name="license_expiry_date"]')?.addEventListener('change', function() {
      const expiryDate = new Date(this.value);
      const today = new Date();
      if (expiryDate < today) {
          alert('⚠️ La licencia de conducción está vencida. No podrás realizar reservaciones.');
      } else {
          const daysUntilExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
          if (daysUntilExpiry < 30) {
              alert(`⚠️ Tu licencia vence en ${daysUntilExpiry} días. Te recomendamos renovarla pronto.`);
          }
      }
  });
})();
