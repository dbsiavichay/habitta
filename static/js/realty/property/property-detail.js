$(function () {
    var image = document.getElementById('cropper_image');
    var input = document.getElementById('base64input');
      
    var $modal = $('#cover-modal');
    var cropper;   
    
    input.addEventListener('change', function (e) {
        var files = e.target.files;
        var done = function (url) {                
            input.value = '';
            image.src = url;          
            modalShow();
        };
        var reader;
        var file;
        var url;

        if (files && files.length > 0) {
            file = files[0];
                  
            if (URL) {
                done(URL.createObjectURL(file));
            } else if (FileReader) {
                reader = new FileReader();
                reader.onload = function (e) {
                    done(reader.result);
                };
                reader.readAsDataURL(file);
            }
        }
    });


    var modalShow =  function () {
        cropper = new Cropper(image, {
            aspectRatio: 16 / 5,
            autoCropArea:1,
            viewMode: 3,
            cropBoxResizable: false,
        });

        $modal.fadeIn();
    }


    $('#crop').on('click', function () {           
        var canvas;
        $modal.fadeOut();            

        if (cropper) {
            canvas = cropper.getCroppedCanvas({
                width: 1920,
                height: 600,
            });                

            $('#id_is_cover').val(true);
            $('#id_base64image').val(canvas.toDataURL());                

            cropper.destroy();
            cropper = null;
            $('#cover_form').submit();
        } 
    });
});