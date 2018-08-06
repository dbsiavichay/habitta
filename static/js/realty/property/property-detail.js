$(function () {
    var image = document.getElementById('cropper_image');
    var coverInput = document.getElementById('base64input');
    var imageInput = document.getElementById('image_input');
      
    var $modal = $('#cover-modal');
    var cropper;

    var getFormData = function(form) {
        var formData = new FormData();
        var elements = form.querySelectorAll('input, select, textarea');
        for( var i = 0; i < elements.length; ++i ) {
            var element = elements[i];
            var name = element.name;
            var value = element.value;

            if(name) {
                formData.append(name, value);
            }
        }

        return formData;
    }

    var uploadImage = function(base64image) {        
        var form = document.getElementById('image_form');
        document.getElementById('id_base64image').value = base64image;
        formData = getFormData(form);    

        $.ajax(form.action, {
            method: form.method,
            data: formData,
            processData: false,
            contentType: false,

            success: function (data) {            
                var galleryItem = document.querySelector('.gallery-item');
                var el = galleryItem.cloneNode(true);
                if (el.classList.contains('hidden')){
                    el.classList.remove('hidden')
                }

                if (el.hasAttribute('style')){
                    el.removeAttribute('style')
                }

                el.querySelector('img').src = data['image_url'];
                el.querySelector('a').href = data['image_url'];

                document.getElementById('gallery').appendChild(el);
                citybook.destroyLightGallery();
            },

            error: function (err) {
                console.log(err);
                //$alert.show().addClass('alert-warning').text('Upload error');
            },

            complete: function () {
                citybook.initLightGallery();
            },
        });
    }

    var modalShow =  function () {
        $modal.fadeIn();
    }

    var createCropper = function (image, ready=False) {
        cropper = new Cropper(image, {
            aspectRatio: 16 / 9,
            autoCropArea:1,
            viewMode: 3,
            cropBoxResizable: false,
        });

        if (!ready) return;

        image.addEventListener('ready', function () {            
            var canvas = this.cropper.getCroppedCanvas({
                width: 800,
                height: 450,
            });

            uploadImage(canvas.toDataURL()); 
            this.cropper.destroy();
            cropper = null;           
        });
    }

    var getDataFile = function(files) {                
        var done = function (url) {        
            coverInput.value = '';
            imageInput.value = '';
            image.src = url;            
        };        

        if (files && files.length > 0) {
            var file = files[0];

            if (URL) {
                done(URL.createObjectURL(file));
            } else if (FileReader) {
                var reader = new FileReader();
                reader.onload = function (e) {
                  done(reader.result);
                };
                reader.readAsDataURL(file);
            }
        }        
    } 

    coverInput.addEventListener('change', function (e) {        
        getDataFile(e.target.files);
        createCropper(image);
        modalShow();
    });
    imageInput.addEventListener('change', function (e) {        
        getDataFile(e.target.files);
        createCropper(image, true);        
    });


    

    var destroyCropper = function () {
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
    }


    document.getElementById('crop').addEventListener('click', function () {           
        var canvas;

        if (cropper) {
            canvas = cropper.getCroppedCanvas({
                width: 1600,
                height: 900,
            });                

            $('#id_is_cover').val(true);
            $('#id_base64image').val(canvas.toDataURL());                            
            $('#image_form').submit();
        } 

        $modal.fadeOut(destroyCropper);            
    });
});