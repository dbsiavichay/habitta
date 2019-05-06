$(function () {
    var coverInput = document.getElementById('cover_image');
    var cropperImage = document.getElementById('cropper_image');

      
    var $modal = $('#cover-modal');
    var cropper;

    var getDataFile = function(files) {                
        prom = new Promise(function (resolve, reject) {
            var done = function (url) {        
                coverInput.value = '';                
                cropperImage.src = url;
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


    var createCropper = function (image) {
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
    } 

    var destroyCropper = function () {
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
    }

    //Cover engine
    var modalShow =  function () {
        $modal.fadeIn();
    }

    document.getElementById('crop').addEventListener('click', function () {           
        data = getBase64Image(1600, 900);
        if (data) {
            document.getElementById('id_base64image').value = data;
            document.getElementById('cover').src = data;
        }
        $modal.fadeOut(destroyCropper);            
    });

    //Cancel crop
    document.querySelectorAll('.close-reg,#cancel-crop').forEach(function (item) {
        item.addEventListener('click', function () { $modal.fadeOut(); destroyCropper(); });        
    })

    //Events
    coverInput.addEventListener('change', function (e) {        
        getDataFile(e.target.files)
        .then(function () {
            createCropper(cropperImage);
            modalShow();            
        });
    });
   
});