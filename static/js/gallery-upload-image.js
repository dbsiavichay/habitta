$(function () {
    var imageInput = document.getElementById('id_img');
      
    // Gallery engine
    var uploadImage = function() {
        var form = document.getElementById('image_form');
        formData = getFormData(form);    

        $.ajax(form.action, {
            method: form.method,
            data: formData,
            processData: false,
            contentType: false,

            success: function (data) {                
                var el = document.querySelector('.gallery-item');
                var galleryItem;
                if (el.classList.contains('hidden')) {
                    galleryItem = el;
                    galleryItem.classList.remove('hidden');
                } else {
                    galleryItem = el.cloneNode(true);
                }

                if (galleryItem.hasAttribute('style')){
                    galleryItem.removeAttribute('style')
                }

                galleryItem.querySelector('img').src = data['image_url'];
                galleryItem.querySelector('.gal-link.popup-image').href = data['image_url'];
                galleryItem.querySelector('.gallery-item-del').href = data['delete_image_url'];

                document.getElementById('gallery').appendChild(galleryItem);
                citybook.destroyLightGallery();                
                unsetDeleteImageGallery();
            },

            error: function (err) {
                console.log(err);
                //$alert.show().addClass('alert-warning').text('Upload error');
            },

            complete: function () {
                citybook.initLightGallery();
                setDeleteImageGallery();
            },
        });
    }

    var deleteImageGallery = function (event) {
        event.preventDefault();
        var self = this;
        $.ajax(self.getAttribute('href'), 
            {
                method: 'POST',
                data:{},
                success: function () {                    
                    $(self).parents('.gallery-item').remove();
                    citybook.destroyLightGallery();
                },
                complete: function () {
                    citybook.initLightGallery();
                },                
                error: function (err) {
                    console.log(err);
                }
            }
        );
    }

    var setDeleteImageGallery = function () {
        $('.gallery-item-del').on('click', deleteImageGallery);        
    }

    var unsetDeleteImageGallery = function () {
        $('.gallery-item-del').off('click', deleteImageGallery);
    }

    setDeleteImageGallery();

    
    //Events
    if(imageInput) {
        imageInput.addEventListener('change', function (e) {        
            uploadImage();
        });
    }
});