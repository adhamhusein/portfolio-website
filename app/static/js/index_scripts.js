function toggleMobileMenu() {
    document.getElementById('menu').classList.toggle('active');
};

document.addEventListener('DOMContentLoaded', function() {
    const swiper = new Swiper('.slider-wrapper', {
        loop: false,
        grabCursor: true,
        spaceBetween: 10,
        pagination: {
            el: '.swiper-pagination',
            clickable: true,
            dynamicBullets: true
        },
        navigation: {
            nextEl: '.swiper-button-next',
            prevEl: '.swiper-button-prev',
        },
        breakpoints: {
            0: { slidesPerView: 1 },
            768: { slidesPerView: 2 },
            1024: { slidesPerView: 3 }
        }
    });
});