 (function () {
    const preloader = document.getElementById('preloader');
    if (!preloader) return;

    function hidePreloader() {
      preloader.classList.add('hide');
      // remove from DOM after transition for performance
      setTimeout(() => preloader.remove(), 450);
    }

    // Hide only after ALL contents load (images, videos, fonts, etc.)
    window.addEventListener('load', hidePreloader);

    // Safety fallback (in case load event gets stuck)
    setTimeout(hidePreloader, 12000);
  })();

const menuBtn = document.getElementById('menuBtn');
  const mobileMenu = document.getElementById('mobileMenu');

  menuBtn.addEventListener('click', () => {
    mobileMenu.classList.toggle('hidden');
  });

function toggleMobileShop() {
    const menu = document.getElementById('mobileShopMenu');
    const arrow = document.getElementById('shopArrow');
    menu.classList.toggle('hidden');
    arrow.classList.toggle('rotate-180');
  }


// revel
const reveals = document.querySelectorAll('.reveal');

const observer = new IntersectionObserver(
    entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                observer.unobserve(entry.target); // animate once
            }
        });
    },
    {
        threshold: 0.15,
    }
);

reveals.forEach(el => observer.observe(el));



// video

const playBtn = document.getElementById('playVideo');
  const video = document.getElementById('videoEl');

  playBtn.addEventListener('click', () => {
    playBtn.classList.add('hidden');
    video.classList.remove('hidden');

    video.muted = false;      // force sound
    video.volume = 1;        // full volume
    video.play();
  });





// year
 document.getElementById('year').textContent = new Date().getFullYear();

const slides = document.querySelectorAll('.banner-slide');
let current = 0;

function showSlide(index){
    slides.forEach(slide => slide.classList.remove('active'));
    slides[index].classList.add('active');
}

function nextSlide(){
    current = (current + 1) % slides.length;
    showSlide(current);
}

function prevSlide(){
    current = (current - 1 + slides.length) % slides.length;
    showSlide(current);
}

setInterval(nextSlide, 6000);
showSlide(current);


const offerTrack = document.querySelector('.offer-slider-track');
const offerSlides = document.querySelectorAll('.offer-slide');
let offerIndex = 0;

function showOffer(index) {
    offerTrack.style.transform = `translateY(-${index * 100}%)`;
}

function nextOffer() {
    offerIndex = (offerIndex + 1) % offerSlides.length;
    showOffer(offerIndex);
}

function prevOffer() {
    offerIndex = (offerIndex - 1 + offerSlides.length) % offerSlides.length;
    showOffer(offerIndex);
}

setInterval(nextOffer, 5000);
showOffer(offerIndex);




new Swiper('.newArrivalsSwiper', {
    loop: true,
    speed: 700,
    spaceBetween: 20,

    // ✅ 2 mobile, 3 tablet, 4 laptop+
    breakpoints: {
      0:   { slidesPerView: 2, spaceBetween: 14 },
      768: { slidesPerView: 3, spaceBetween: 18 },
      1024:{ slidesPerView: 4, spaceBetween: 20 }
    },

    navigation: {
      nextEl: '.newArrivalsNext',
      prevEl: '.newArrivalsPrev',
    },

    pagination: {
      el: '.newArrivalsPagination',
      clickable: true,
    },

    autoplay: {
      delay: 3000,
      disableOnInteraction: false,
      pauseOnMouseEnter: true
    }
  });



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


  document.addEventListener("DOMContentLoaded", function () {

    const slider = document.querySelector(".banner-slider");
    if (!slider) return; // safety

    const slides = slider.querySelectorAll(".banner-slide");
    const prevBtn = slider.querySelector(".nav.prev");
    const nextBtn = slider.querySelector(".nav.next");

    let currentIndex = 0;
    const totalSlides = slides.length;

    if (totalSlides === 0) return;

    // Ensure only first slide is active initially
    slides.forEach((slide, i) => {
        slide.classList.toggle("active", i === 0);
    });

    function showSlide(index) {
        slides.forEach(slide => slide.classList.remove("active"));
        slides[index].classList.add("active");
    }

    function nextSlide() {
        currentIndex = (currentIndex + 1) % totalSlides;
        showSlide(currentIndex);
    }

    function prevSlide() {
        currentIndex = (currentIndex - 1 + totalSlides) % totalSlides;
        showSlide(currentIndex);
    }

    // Button events
    if (nextBtn) nextBtn.addEventListener("click", nextSlide);
    if (prevBtn) prevBtn.addEventListener("click", prevSlide);

    // Auto play
    let autoPlay = setInterval(nextSlide, 5000);

    // Pause on hover
    slider.addEventListener("mouseenter", () => clearInterval(autoPlay));
    slider.addEventListener("mouseleave", () => {
        autoPlay = setInterval(nextSlide, 5000);
    });

});
