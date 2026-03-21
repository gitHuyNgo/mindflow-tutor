// Module-level store for passing MediaStream objects between pages
// (MediaStream cannot be serialized through React Router state / history.pushState)
export const sessionStore = {
  camStream: null as MediaStream | null,
  screenStream: null as MediaStream | null,
  micOn: false,
  camOn: false,
};
