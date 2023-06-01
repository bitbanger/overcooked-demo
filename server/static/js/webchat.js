// var socket = io();

const msgerForm = get(".msger-inputarea");
const msgerInput = get(".msger-input");
const msgerChat = get(".msger-chat");

const BOT_MSGS = [
"Hi, how are you?",
"Ohh... I can't understand what you trying to say. Sorry!",
"I like to play games... But I don't know how to play!",
"Sorry if my answers are not relevant. :))",
"I feel sleepy! :("];


// Icons made by Freepik from www.flaticon.com
const BOT_IMG = "static/images/val_icon.svg";
const PERSON_IMG = "static/images/usr_icon.svg";
const BOT_NAME = "VAL";
const PERSON_NAME = "You";

socket.on('valmsg', function(data) {
	botResponse(data['msg']);
});

$(document).ready(function() {
	document.addEventListener('click', function(event) {
		if(event.target) {
			if ( (event.target.className == 'msger-yes-btn') || (event.target.className == 'msger-no-btn') ) {
				// console.log(event.target.id);
				event.preventDefault();
				var msg = 'Y';
				if (event.target.className == 'msger-no-btn') {
					msg = 'N';
				}
				socket.emit('message', {'msg': msg});
				$(event.target).prop("disabled", true);
				//$(event.target).css("background-color", "gray");
				$(event.target).siblings(":button").prop("disabled", true);
				$(event.target).siblings(":button").css("background-color", "gray");
			}
		}
	});
});

msgerForm.addEventListener("submit", event => {
  event.preventDefault();

  const msgText = msgerInput.value;
  if (!msgText) return;

  socket.emit('message', {'msg': msgText})

  appendMessage(PERSON_NAME, PERSON_IMG, "right", msgText);
  msgerInput.value = "";
});

function appendMessage(name, img, side, text) {
  //   Simple solution for small apps
  const msgHTML = `
    <div class="msg ${side}-msg">
      <div class="msg-img" style="background-image: url(${img})"></div>

      <div class="msg-bubble">
        <div class="msg-info">
          <div class="msg-info-name">${name}</div>
          <div class="msg-info-time">${formatDate(new Date())}</div>
        </div>

        <div class="msg-text">${text}</div>
      </div>
    </div>
  `;

  msgerChat.insertAdjacentHTML("beforeend", msgHTML);
  msgerChat.scrollTop += 500;
}

function botResponse(msgText) {
  // const delay = msgText.split(" ").length * 100;

  // setTimeout(() => {
    appendMessage(BOT_NAME, BOT_IMG, "left", msgText);
  // }, delay);
}

// Utils
function get(selector, root = document) {
  return root.querySelector(selector);
}

function formatDate(date) {
  const h = "0" + date.getHours();
  const m = "0" + date.getMinutes();

  return `${h.slice(-2)}:${m.slice(-2)}`;
}

function random(min, max) {
  return Math.floor(Math.random() * (max - min) + min);
}
