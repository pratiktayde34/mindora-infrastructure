// static/js/custom.js
$(document).ready(function() {
	// toggle chat UI
	$('.chat_icon').click(function() {
	  $('.chat_box').toggleClass('active');
	});
  
	// convform initialization (keep same options)
	$('.my-conv-form-wrapper').convform({ selectInputStyle: 'disable' });
  });
  
  /*
   * ConvForm callback function.
   * convState: the ConvState object (see jquery.convform.js)
   * readyCallback: call when response is ready so convform continues the flow
   */
  function handleChat(convState, readyCallback) {
	// Get text the user just entered
	var userMessage = '';
	if (convState && convState.current && convState.current.answer) {
	  // convState.current.answer may be a string or object
	  userMessage = (typeof convState.current.answer === 'string') ?
					convState.current.answer :
					(convState.current.answer.text || '');
	}
  
	// If empty, just continue
	if (!userMessage || userMessage.trim() === '') {
	  // supply a fallback reply and loop
	  convState.current.input.questions = ["Please type something so I can help you."];
	  convState.current.next = convState.current;
	  readyCallback();
	  return;
	}
  
	// POST to your backend endpoint that talks to Gemini (/chatbot)
	$.ajax({
	  url: '/chatbot',            // Flask route you will create
	  method: 'POST',
	  data: { message: userMessage },
	  success: function(response) {
		// If your server returns JSON, adjust: response.reply
		var replyText = response;
		if (typeof response === 'object' && response.reply) replyText = response.reply;
  
		// Inject the LLM reply so convform prints it as the bot message
		convState.current.input.questions = [replyText];
  
		// Keep the conversation going (loop this state)
		convState.current.next = convState.current;
  
		// Tell convform to proceed
		readyCallback();
	  },
	  error: function() {
		convState.current.input.questions = ["Sorry, I couldn't reach the server. Try again soon."];
		convState.current.next = convState.current;
		readyCallback();
	  }
	});
  }
  

