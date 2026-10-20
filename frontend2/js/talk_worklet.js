/** Microphone capture for talk.js: hands each block of samples to the page. */
class RaprCapture extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) this.port.postMessage(ch.slice(0));
    return true;
  }
}
registerProcessor('rapr-capture', RaprCapture);
