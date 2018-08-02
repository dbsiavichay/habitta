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

    var cropper = new Cropper(img, {
        aspectRatio: 16 / 9,
        autoCropArea:1,
        viewMode: 3,
        cropBoxResizable: false,
        ready: function () {
            debugger;
            var canvas = this.cropper.getCroppedCanvas({
                width: 800,
                height: 450,
            });
            /*var clone = this.cloneNode();

            clone.className = ''
            clone.style.cssText = (
              'display: block;' +
              'width: 100%;' +
              'min-width: 0;' +
              'min-height: 0;' +
              'max-width: none;' +
              'max-height: none;'
            );

            each(previews, function (elem) {
              elem.appendChild(clone.cloneNode());
            });*/
          },
    });
            
    debugger;
    /*var canvas = cropper.getCroppedCanvas({
        width: 800,
        height: 450,
    });

    //initialAvatarURL = avatar.src;
    //avatar.src = canvas.toDataURL();              
  
    canvas.toBlob(function (blob) {
        var form = document.getElementById('image_form');
        formData = getFormData(form);
        formData.append('img', blob);

        $.ajax(form.action, {
            method: form.method,
            data: formData,
            processData: false,
            contentType: false,

            xhr: function () {
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
            },

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
    });*/
}); 