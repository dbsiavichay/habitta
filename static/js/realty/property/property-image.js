var inputImg = document.getElementById('id_img');
        
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

var uploadImage = function(blob) {    
    var form = document.getElementById('image_form');
    formData = getFormData(form);
    formData.append('img', blob);

    $.ajax(form.action, {
        method: form.method,
        data: formData,
        processData: false,
        contentType: false,

        /*xhr: function () {
            var xhr = new XMLHttpRequest();

            xhr.upload.onprogress = function (e) {
                console.log(e);
                var percent = '0';
                var percentage = '0%';

                if (e.lengthComputable) {
                    percent = Math.round((e.loaded / e.total) * 100);
                    percentage = percent + '%';
                    //$progressBar.width(percentage).attr('aria-valuenow', percent).text(percentage);
                }
            };

            return xhr;
        },*/

        success: function (data) {
            console.log(data);
            //$alert.show().addClass('alert-success').text('Upload success');
        },

        error: function (err) {
            console.log(err);
            //$alert.show().addClass('alert-warning').text('Upload error');
        },

        complete: function () {
            console.log('sa');
            //$progress.hide();
        },
    });
}


var createCropper = function (image) {
    var cropper = new Cropper(image, {
        aspectRatio: 16 / 9,
        autoCropArea:1,
        viewMode: 3,
        cropBoxResizable: false,
        ready: function () {            
            var canvas = this.cropper.getCroppedCanvas({
                width: 800,
                height: 450,
            });

            canvas.toBlob(uploadImage); 
            this.cropper.destroy();           
        },
    });
}

inputImg.addEventListener('change', function (e) { 
    var img = document.getElementById('img');           
    var files = e.target.files;
    var done = function (url) {
        inputImg.value = '';
        img.src = url;
    };
    var reader;
    var file;            

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

    createCropper(img);    
}); 