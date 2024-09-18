$(document).ready(function(){
	var current_fs, next_fs, previous_fs; //fieldsets
	var opacity;
	var current = 1;
	var steps = $("fieldset").length;

	setProgressBar(current);

	$(".next").click(function(){
		article = sessionStorage.getItem("article");
		if(article!=""){

			current_fs = $(this).parent();
			next_fs = $(this).parent().next();

			//Add Class Active
			$("#progressbar li").eq($("fieldset").index(next_fs)).addClass("active");

			//show the next fieldset
			next_fs.show();

			//hide the current fieldset with style
			current_fs.animate({opacity: 0}, {
				step: function(now) {
					// for making fielset appear animation
					opacity = 1 - now;

					current_fs.css({
					'display': 'none',
					'position': 'relative'
					});

					next_fs.css({'opacity': opacity});
				},
				duration: 500
			});

			setProgressBar(++current);
			$('fieldset').removeClass('d-none');
			$('fieldset').removeClass('d-block');
			$('fieldset').addClass('d-none');
			$('#fieldset_'+(current-1)).removeClass('d-none');
			$('#fieldset_'+(current-1)).addClass('d-block');
		}
	});

	$(".previous").click(function(){
		article = sessionStorage.getItem("article");
		if(article!=""){

			current_fs = $(this).parent();
			previous_fs = $(this).parent().prev();

			//Remove class active
			$("#progressbar li").eq($("fieldset").index(current_fs)).removeClass("active");

			//show the previous fieldset
			previous_fs.show();

			//hide the current fieldset with style
			current_fs.animate({opacity: 0}, {
				step: function(now) {
					// for making fielset appear animation
					opacity = 1 - now;

					current_fs.css({
					'display': 'none',
					'position': 'relative'
					});
					
					previous_fs.css({'opacity': opacity});
				},
				duration: 500
			});
			setProgressBar(--current);

			$('fieldset').removeClass('d-none');
			$('fieldset').removeClass('d-block');
			$('fieldset').addClass('d-none');
			$('#fieldset_'+(current-1)).removeClass('d-none');
			$('#fieldset_'+(current-1)).addClass('d-block');
		}
	});

	window.decrease = function(){
		console.log("Reporting decrease function");
		// while(current>1){
		// 	$("#progressbar li:nth-child("+(current)+")").removeClass("active");
		// 	current = current - 1;
		// }

		current = 1;
		$(".progress-bar").css("width", parseFloat(100 / steps)+"%");
		$("#progressbar li").removeClass("active");
		$("#progressbar li:nth-child("+(current)+")").addClass("active");

	}

	function setProgressBar(curStep){
		var percent = parseFloat(100 / steps) * curStep;
		percent = percent.toFixed();
		$(".progress-bar").css("width", percent+"%");
	}

	window.step_function = function(){
		setProgressBar(--current);

		$("#progressbar li").removeClass("active");
		$("#progressbar li:nth-child("+(current)+")").addClass("active");

		$('fieldset').removeClass('d-none');
		$('fieldset').removeClass('d-block');
		$('fieldset').addClass('d-none');
		$('#fieldset_'+(current-1)).removeClass('d-none');
		$('#fieldset_'+(current-1)).addClass('d-block');
	}

	$(".submit").click(function(){
		return false;
	})
});