document.addEventListener(
  "error",
  (event) => {
    const image = event.target;
    if (!(image instanceof HTMLImageElement) || !image.classList.contains("course-thumbnail-image")) {
      return;
    }

    const frame = image.closest(
      ".course-image-frame, .course-thumb-wrap, .course-thumbnail-box, .card-thumb",
    );
    if (!frame) {
      return;
    }

    image.hidden = true;
    frame.classList.add("course-image-failed");
  },
  true,
);
