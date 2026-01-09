// static/js/adminpanel.js
// (or static/adminpanel/js/adminpanel.js depending on your folder structure)

document.addEventListener("DOMContentLoaded", function () {

    /* ================= MULTIPLE IMAGE PREVIEW & MANAGEMENT ================= */
    const imageInput = document.getElementById("productImages");
    const previewContainer = document.getElementById("imagePreview");
    const deleteImagesInput = document.getElementById("deleteImages");
    const addMoreBtn = document.getElementById("addMoreImages");

    let newSelectedFiles = [];
    let imagesToDelete = [];

    // Delete existing images (from database - Edit mode)
    document.querySelectorAll('.delete-existing').forEach(btn => {
        btn.addEventListener('click', function () {
            const container = this.closest('.existing-image');
            const imgId = container.getAttribute('data-id');

            imagesToDelete.push(imgId);
            deleteImagesInput.value = imagesToDelete.join(',');

            // Visual feedback: fade and checkmark
            container.style.opacity = '0.5';
            this.innerHTML = '✓';
            this.disabled = true;
        });
    });

    // "Add More Images" button triggers file input
    if (addMoreBtn) {
        addMoreBtn.addEventListener('click', () => imageInput.click());
    }

    // Handle new image selection (append to existing selections)
    if (imageInput) {
        imageInput.addEventListener("change", function () {
            const files = Array.from(this.files).filter(f => f.type.startsWith('image/'));
            newSelectedFiles = newSelectedFiles.concat(files);
            renderNewPreviews();
        });
    }

    function renderNewPreviews() {
        previewContainer.innerHTML = "";

        newSelectedFiles.forEach((file, index) => {
            const reader = new FileReader();
            reader.onload = function (e) {
                const wrapper = document.createElement("div");
                wrapper.className = "position-relative border rounded p-2 shadow-sm";

                const img = document.createElement("img");
                img.src = e.target.result;
                img.style.width = "120px";
                img.style.height = "120px";
                img.style.objectFit = "cover";
                img.className = "rounded";

                const removeBtn = document.createElement("button");
                removeBtn.type = "button";
                removeBtn.innerHTML = "&times;";
                removeBtn.className = "btn btn-danger btn-sm position-absolute top-0 end-0 translate-middle rounded-circle";
                removeBtn.onclick = () => {
                    newSelectedFiles.splice(index, 1);
                    renderNewPreviews();
                    updateFileInput();
                };

                wrapper.appendChild(img);
                wrapper.appendChild(removeBtn);
                previewContainer.appendChild(wrapper);
            };
            reader.readAsDataURL(file);
        });

        updateFileInput();
    }

    function updateFileInput() {
        const dt = new DataTransfer();
        newSelectedFiles.forEach(file => dt.items.add(file));
        imageInput.files = dt.files;
    }


    /* ================= THUMBNAIL PREVIEW ================= */
    const thumbnailInput = document.getElementById("thumbnailInput");
    const thumbnailPreview = document.getElementById("thumbnailPreview");

    if (thumbnailInput && thumbnailPreview) {
        thumbnailInput.addEventListener("change", function () {
            const file = this.files[0];
            if (file && file.type.startsWith("image/")) {
                thumbnailPreview.src = URL.createObjectURL(file);
                thumbnailPreview.classList.remove("d-none");
            }
        });
    }


    /* ================= VIDEO PREVIEW ================= */
    const videoInput = document.getElementById("productVideoInput");
    const videoPreview = document.getElementById("productVideoPreview");

    if (videoInput && videoPreview) {
        videoInput.addEventListener("change", function () {
            const file = this.files[0];
            if (file && file.type.startsWith("video/")) {
                videoPreview.src = URL.createObjectURL(file);
                videoPreview.classList.remove("d-none");
            }
        });
    }


    /* ================= DELETE CONFIRMATION (for product list page) ================= */
    let deleteUrl = "";
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            deleteUrl = this.getAttribute('data-delete-url');
        });
    });

    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function () {
            if (deleteUrl) {
                window.location.href = deleteUrl;
            }
        });
    }
});