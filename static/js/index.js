document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.nav');
  const bubble = document.querySelector('.nav-bubble');
  const links = nav ? nav.querySelectorAll('a') : [];

  links.forEach(link => {
    link.addEventListener('mouseenter', function() {
      const rect = this.getBoundingClientRect();
      const navRect = nav.getBoundingClientRect();
      
      bubble.style.left = (rect.left - navRect.left) + 'px';
      bubble.style.width = rect.width + 'px';
      bubble.style.height = rect.height + 'px';
    });
  });

  nav?.addEventListener('mouseleave', () => {
    bubble.style.width = '0';
  });
});
