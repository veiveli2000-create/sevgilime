const surpriseButton = document.querySelector(".surprise-button");
const surpriseNote = document.querySelector("#surprise-note");

if (surpriseButton && surpriseNote) {
  surpriseButton.addEventListener("click", () => {
    const isExpanded = surpriseButton.getAttribute("aria-expanded") === "true";
    surpriseButton.setAttribute("aria-expanded", String(!isExpanded));
    surpriseNote.hidden = isExpanded;
    surpriseButton.textContent = isExpanded ? "Bir sürpriz notun var" : "Notu gizle";
  });
}

const photoGrid = document.querySelector(".photo-grid");
const photoCards = document.querySelectorAll(".photo-card");
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const photoViewer = document.querySelector(".photo-viewer");
const viewerImage = document.querySelector(".viewer-image");
const viewerCaption = document.querySelector(".viewer-caption");
const viewerCloseButton = document.querySelector(".viewer-close");
const viewerPreviousButton = document.querySelector(".viewer-previous");
const viewerNextButton = document.querySelector(".viewer-next");
const photoButtons = document.querySelectorAll(".photo-open");

if (photoViewer && viewerImage && viewerCaption && photoButtons.length) {
  const photos = Array.from(photoButtons, (button) => ({
    image: button.querySelector("img"),
    caption: button.parentElement.querySelector("figcaption").textContent.trim()
  }));
  let activePhotoIndex = 0;

  const showPhoto = (index) => {
    activePhotoIndex = (index + photos.length) % photos.length;
    const photo = photos[activePhotoIndex];
    viewerImage.src = photo.image.currentSrc || photo.image.src;
    viewerImage.alt = photo.image.alt;
    viewerCaption.textContent = photo.caption;
  };

  photoButtons.forEach((button, index) => {
    button.addEventListener("click", () => {
      showPhoto(index);
      photoViewer.showModal();
    });
  });

  viewerCloseButton.addEventListener("click", () => photoViewer.close());
  viewerPreviousButton.addEventListener("click", () => showPhoto(activePhotoIndex - 1));
  viewerNextButton.addEventListener("click", () => showPhoto(activePhotoIndex + 1));

  photoViewer.addEventListener("click", (event) => {
    if (event.target === photoViewer) {
      photoViewer.close();
    }
  });

  photoViewer.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") {
      showPhoto(activePhotoIndex - 1);
    } else if (event.key === "ArrowRight") {
      showPhoto(activePhotoIndex + 1);
    }
  });
}

if (photoGrid && photoCards.length && "IntersectionObserver" in window && !prefersReducedMotion) {
  photoCards.forEach((card, index) => {
    card.style.transitionDelay = `${(index % 3) * 90}ms`;
  });
  photoGrid.classList.add("gallery-reveal-ready");

  const photoObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  photoCards.forEach((card) => photoObserver.observe(card));
}
