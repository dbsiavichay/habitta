$(function () {
    var image = document.getElementById('cropper_image');
    var coverInput = document.getElementById('base64input');
    var imageInput = document.getElementById('image_input');
      
    var $modal = $('#cover-modal');
    var cropper;

    var getDataFile = function(files) {                
        prom = new Promise(function (resolve, reject) {
            var done = function (url) {        
                coverInput.value = '';
                imageInput.value = '';
                image.src = url;
                resolve();
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
        });

        return prom;
    }

    var getBase64Image = function(width, height){
        if (!cropper) return null;
        var canvas = cropper.getCroppedCanvas({
            width: width,
            height: height,
        });

        return canvas.toDataURL(); 
    }


    var createCropper = function (image, ready=false) {
        if (cropper) {
            cropper.element = image
        } else {
            cropper = new Cropper(image, {
                aspectRatio: 16 / 9,
                autoCropArea:1,
                viewMode: 3,
                cropBoxResizable: false,
            });
        }
        
        if (!ready) return;
        image.addEventListener('ready', uploadImage);
    } 

    var destroyCropper = function () {
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }

        if (image) {
            image.removeEventListener('ready', uploadImage);            
        }
    }

    // Gallery engine
    var uploadImage = function() {
        data = getBase64Image(800,450);
        if (!data) return;

        var form = document.getElementById('image_form');
        document.getElementById('id_is_cover').value = false;
        document.getElementById('id_base64image').value = data;
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
                destroyCropper();
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

    //Cover engine
    var modalShow =  function () {
        $modal.fadeIn();
    }

    document.getElementById('crop').addEventListener('click', function () {           
        data = getBase64Image(1600, 900);

        if (data) {
            document.getElementById('id_is_cover').value = true;        
            document.getElementById('id_base64image').value = data;        
            document.getElementById('image_form').submit();            
        } 

        $modal.fadeOut(destroyCropper);            
    });

    document.querySelectorAll('.close-reg,#cancel-crop').forEach(function (item) {
        item.addEventListener('click', function () { $modal.fadeOut(); destroyCropper(); });        
    })

    //Events
    coverInput.addEventListener('change', function (e) {        
        getDataFile(e.target.files)
        .then(function () {
            createCropper(image);
            modalShow();            
        });
    });
    imageInput.addEventListener('change', function (e) {        
        getDataFile(e.target.files)
        .then(function () {
            createCropper(image, true);                    
        });
    });


    
});