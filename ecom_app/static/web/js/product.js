   const mainImage = document.getElementById('mainImage');
        const thumbs = document.querySelectorAll('.thumbBtn');
        const thumbsM = document.querySelectorAll('.thumbBtnM');

        function setActiveThumb(btns, activeBtn) {
            btns.forEach(b => {
                b.classList.remove('border-2', 'border-brownMain');
                b.classList.add('border', 'border-line');
            });
            activeBtn.classList.remove('border', 'border-line');
            activeBtn.classList.add('border-2', 'border-brownMain');
        }

        function swapImage(src) {
            if (!src) return;
            mainImage.src = src;
        }

        thumbs.forEach(btn => {
            btn.addEventListener('click', () => {
                const src = btn.getAttribute('data-img');
                swapImage(src);
                setActiveThumb(thumbs, btn);
            });
        });

        thumbsM.forEach(btn => {
            btn.addEventListener('click', () => {
                const src = btn.getAttribute('data-img');
                swapImage(src);
                setActiveThumb(thumbsM, btn);
            });
        });

        const zoomContainer = document.getElementById('zoomContainer');
  const zoomImage = document.getElementById('mainImage');

  zoomContainer.addEventListener('mouseenter', () => {
    zoomImage.style.transform = 'scale(1.8)';
  });

  zoomContainer.addEventListener('mousemove', (e) => {
    const rect = zoomContainer.getBoundingClientRect();

    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    zoomImage.style.transformOrigin = `${x}% ${y}%`;
  });

  zoomContainer.addEventListener('mouseleave', () => {
    zoomImage.style.transform = 'scale(1)';
    zoomImage.style.transformOrigin = 'center center';
  });