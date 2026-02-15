import SwiftUI
import SpriteKit

struct ContentView: View {
    @StateObject private var gameState = GameState()

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            GeometryReader { geometry in
                SpriteView(scene: gameState.makeScene(size: geometry.size))
                    .ignoresSafeArea()
            }
        }
    }
}

class GameState: ObservableObject {
    private var scene: GameScene?

    func makeScene(size: CGSize) -> GameScene {
        if let existing = scene {
            return existing
        }
        let newScene = GameScene(size: size)
        newScene.scaleMode = .resizeFill
        scene = newScene
        return newScene
    }
}
