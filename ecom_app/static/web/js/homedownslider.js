 (function () {
    const slider = document.getElementById("kmSlider");
    const track  = document.getElementById("kmTrack");
    const prevBtn = document.getElementById("kmPrev");
    const nextBtn = document.getElementById("kmNext");
    const dotsWrap = document.getElementById("kmDots");

    const slides = Array.from(track.children);
    const total = slides.length;

    let index = 0;
    let autoplay = true;
    let timer = null;

    // Build dots
    const dots = slides.map((_, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "h-2.5 w-2.5 rounded-full bg-white/40 hover:bg-white/70 transition";
      b.setAttribute("aria-label", "Go to slide " + (i + 1));
      b.addEventListener("click", () => goTo(i, true));
      dotsWrap.appendChild(b);
      return b;
    });

    function setActiveDot() {
      dots.forEach((d, i) => {
        d.className = "h-2.5 w-2.5 rounded-full transition " + (i === index
          ? "bg-white"
          : "bg-white/40 hover:bg-white/70");
      });
    }

    function goTo(i, userAction = false) {
      index = (i + total) % total;
      track.style.transform = `translateX(-${index * 100}%)`;
      setActiveDot();
      if (userAction) restartAuto();
    }

    function next(userAction = false) { goTo(index + 1, userAction); }
    function prev(userAction = false) { goTo(index - 1, userAction); }

    function startAuto() {
      if (!autoplay) return;
      stopAuto();
      timer = setInterval(() => next(false), 4500);
    }
    function stopAuto() {
      if (timer) clearInterval(timer);
      timer = null;
    }
    function restartAuto() {
      if (!autoplay) return;
      stopAuto();
      startAuto();
    }

    // Buttons
    nextBtn.addEventListener("click", () => next(true));
    prevBtn.addEventListener("click", () => prev(true));

    // Pause on hover (desktop)
    slider.addEventListener("mouseenter", stopAuto);
    slider.addEventListener("mouseleave", startAuto);

    // Touch swipe (mobile)
    let startX = 0, dx = 0, touching = false;

    slider.addEventListener("touchstart", (e) => {
      touching = true;
      startX = e.touches[0].clientX;
      dx = 0;
      stopAuto();
    }, { passive: true });

    slider.addEventListener("touchmove", (e) => {
      if (!touching) return;
      dx = e.touches[0].clientX - startX;
    }, { passive: true });

    slider.addEventListener("touchend", () => {
      touching = false;
      if (Math.abs(dx) > 50) {
        dx < 0 ? next(true) : prev(true);
      }
      startAuto();
    });

    // Init
    goTo(0, false);
    startAuto();

    // Optional: expose a quick toggle
    // window.kmSliderAuto = (v) => { autoplay = !!v; autoplay ? startAuto() : stopAuto(); };
  })();