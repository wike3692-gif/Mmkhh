import SpriteKit

class GameScene: SKScene, SKPhysicsContactDelegate {

    // MARK: - Category Bitmasks

    private struct Category {
        static let ball:   UInt32 = 0x1 << 0
        static let paddle: UInt32 = 0x1 << 1
        static let block:  UInt32 = 0x1 << 2
        static let wall:   UInt32 = 0x1 << 3
        static let bottom: UInt32 = 0x1 << 4
    }

    // MARK: - Properties

    private var paddle: SKShapeNode!
    private var ball: SKShapeNode!
    private var scoreLabel: SKLabelNode!
    private var livesLabel: SKLabelNode!
    private var messageLabel: SKLabelNode!
    private var subMessageLabel: SKLabelNode!

    private var score = 0
    private var lives = 3
    private var blockCount = 0
    private var isPlaying = false
    private var didSetup = false

    private let ballSpeed: CGFloat = 420
    private let ballRadius: CGFloat = 8
    private let rows = 6
    private let cols = 8

    // MARK: - Block Colors

    private let blockColors: [(fill: SKColor, glow: SKColor)] = [
        (SKColor(red: 1.0, green: 0.25, blue: 0.25, alpha: 1.0), SKColor(red: 1.0, green: 0.4, blue: 0.4, alpha: 0.6)),
        (SKColor(red: 1.0, green: 0.55, blue: 0.15, alpha: 1.0), SKColor(red: 1.0, green: 0.65, blue: 0.3, alpha: 0.6)),
        (SKColor(red: 1.0, green: 0.9,  blue: 0.2,  alpha: 1.0), SKColor(red: 1.0, green: 0.95, blue: 0.4, alpha: 0.6)),
        (SKColor(red: 0.2, green: 0.9,  blue: 0.4,  alpha: 1.0), SKColor(red: 0.3, green: 1.0, blue: 0.5, alpha: 0.6)),
        (SKColor(red: 0.3, green: 0.75, blue: 1.0,  alpha: 1.0), SKColor(red: 0.4, green: 0.85, blue: 1.0, alpha: 0.6)),
        (SKColor(red: 0.65, green: 0.5, blue: 1.0,  alpha: 1.0), SKColor(red: 0.75, green: 0.6, blue: 1.0, alpha: 0.6)),
    ]

    // MARK: - Scene Lifecycle

    override func didMove(to view: SKView) {
        guard !didSetup else { return }
        didSetup = true

        backgroundColor = SKColor(red: 0.04, green: 0.04, blue: 0.1, alpha: 1.0)

        physicsWorld.gravity = .zero
        physicsWorld.contactDelegate = self

        setupWalls()
        setupBottomEdge()
        setupPaddle()
        setupBall()
        setupBlocks()
        setupLabels()
        showMessage("ブロック崩し", sub: "タップしてスタート")
    }

    // MARK: - Setup

    private func setupWalls() {
        let border = SKPhysicsBody(edgeLoopFrom: frame)
        border.categoryBitMask = Category.wall
        border.friction = 0
        border.restitution = 1.0
        physicsBody = border
    }

    private func setupBottomEdge() {
        let bottomLine = CGRect(x: frame.minX, y: frame.minY - 20, width: frame.width, height: 1)
        let bottom = SKNode()
        bottom.name = "bottom"
        bottom.physicsBody = SKPhysicsBody(edgeLoopFrom: bottomLine)
        bottom.physicsBody?.categoryBitMask = Category.bottom
        bottom.physicsBody?.contactTestBitMask = Category.ball
        addChild(bottom)
    }

    private func setupPaddle() {
        let paddleWidth = frame.width * 0.24
        let paddleHeight: CGFloat = 14
        let cornerRadius: CGFloat = 7

        let rect = CGRect(x: -paddleWidth / 2, y: -paddleHeight / 2, width: paddleWidth, height: paddleHeight)
        paddle = SKShapeNode(rect: rect, cornerRadius: cornerRadius)
        paddle.fillColor = .white
        paddle.strokeColor = SKColor(white: 1.0, alpha: 0.5)
        paddle.lineWidth = 1
        paddle.position = CGPoint(x: frame.midX, y: frame.minY + 60)
        paddle.name = "paddle"

        // Glow effect
        let glow = SKShapeNode(rect: rect.insetBy(dx: -3, dy: -3), cornerRadius: cornerRadius + 3)
        glow.fillColor = SKColor(white: 1.0, alpha: 0.15)
        glow.strokeColor = .clear
        glow.zPosition = -1
        paddle.addChild(glow)

        paddle.physicsBody = SKPhysicsBody(rectangleOf: CGSize(width: paddleWidth, height: paddleHeight))
        paddle.physicsBody?.isDynamic = false
        paddle.physicsBody?.categoryBitMask = Category.paddle
        paddle.physicsBody?.contactTestBitMask = Category.ball
        paddle.physicsBody?.friction = 0
        paddle.physicsBody?.restitution = 1.0
        addChild(paddle)
    }

    private func setupBall() {
        ball = SKShapeNode(circleOfRadius: ballRadius)
        ball.fillColor = SKColor(red: 1.0, green: 0.95, blue: 0.4, alpha: 1.0)
        ball.strokeColor = SKColor(red: 1.0, green: 1.0, blue: 0.7, alpha: 0.8)
        ball.lineWidth = 1
        ball.glowWidth = 3
        ball.name = "ball"
        ball.position = CGPoint(x: frame.midX, y: paddle.position.y + 24)

        ball.physicsBody = SKPhysicsBody(circleOfRadius: ballRadius)
        ball.physicsBody?.isDynamic = true
        ball.physicsBody?.affectedByGravity = false
        ball.physicsBody?.allowsRotation = false
        ball.physicsBody?.friction = 0
        ball.physicsBody?.restitution = 1.0
        ball.physicsBody?.linearDamping = 0
        ball.physicsBody?.angularDamping = 0
        ball.physicsBody?.categoryBitMask = Category.ball
        ball.physicsBody?.contactTestBitMask = Category.block | Category.paddle | Category.bottom
        ball.physicsBody?.collisionBitMask = Category.wall | Category.paddle | Category.block
        addChild(ball)

        // Trail effect
        if let trail = createBallTrail() {
            trail.targetNode = self
            ball.addChild(trail)
        }
    }

    private func createBallTrail() -> SKEmitterNode? {
        let trail = SKEmitterNode()
        trail.particleBirthRate = 60
        trail.particleLifetime = 0.3
        trail.particleLifetimeRange = 0.1
        trail.emissionAngle = 0
        trail.emissionAngleRange = CGFloat.pi * 2
        trail.particleSpeed = 0
        trail.particleSize = CGSize(width: 6, height: 6)
        trail.particleSizeRange = 2
        trail.particleAlpha = 0.4
        trail.particleAlphaSpeed = -1.5
        trail.particleColor = SKColor(red: 1.0, green: 0.95, blue: 0.4, alpha: 1.0)
        trail.particleColorBlendFactor = 1.0
        trail.particleBlendMode = .add
        return trail
    }

    private func setupBlocks() {
        let sideMargin: CGFloat = 12
        let blockSpacing: CGFloat = 4
        let topOffset = frame.maxY - 120
        let availableWidth = frame.width - sideMargin * 2
        let blockWidth = (availableWidth - blockSpacing * CGFloat(cols - 1)) / CGFloat(cols)
        let blockHeight: CGFloat = 18
        let cornerRadius: CGFloat = 4

        blockCount = 0

        for row in 0..<rows {
            for col in 0..<cols {
                let x = sideMargin + blockWidth / 2 + CGFloat(col) * (blockWidth + blockSpacing)
                let y = topOffset - CGFloat(row) * (blockHeight + blockSpacing)

                let colorPair = blockColors[row % blockColors.count]

                let rect = CGRect(x: -blockWidth / 2, y: -blockHeight / 2, width: blockWidth, height: blockHeight)
                let block = SKShapeNode(rect: rect, cornerRadius: cornerRadius)
                block.fillColor = colorPair.fill
                block.strokeColor = colorPair.glow
                block.lineWidth = 0.5
                block.position = CGPoint(x: x, y: y)
                block.name = "block"
                block.zPosition = 1

                // Highlight on top of block
                let highlight = SKShapeNode(
                    rect: CGRect(x: -blockWidth / 2 + 2, y: 1, width: blockWidth - 4, height: blockHeight / 2 - 2),
                    cornerRadius: 2
                )
                highlight.fillColor = SKColor(white: 1.0, alpha: 0.2)
                highlight.strokeColor = .clear
                block.addChild(highlight)

                block.physicsBody = SKPhysicsBody(rectangleOf: CGSize(width: blockWidth, height: blockHeight))
                block.physicsBody?.isDynamic = false
                block.physicsBody?.categoryBitMask = Category.block
                block.physicsBody?.contactTestBitMask = Category.ball
                block.physicsBody?.friction = 0
                block.physicsBody?.restitution = 1.0

                // Entrance animation
                block.alpha = 0
                block.setScale(0.5)
                let delay = Double(row) * 0.05 + Double(col) * 0.02
                block.run(.sequence([
                    .wait(forDuration: delay),
                    .group([
                        .fadeIn(withDuration: 0.3),
                        .scale(to: 1.0, duration: 0.3)
                    ])
                ]))

                addChild(block)
                blockCount += 1
            }
        }
    }

    private func setupLabels() {
        scoreLabel = SKLabelNode(fontNamed: "Avenir-Heavy")
        scoreLabel.fontSize = 18
        scoreLabel.fontColor = SKColor(white: 0.9, alpha: 1.0)
        scoreLabel.horizontalAlignmentMode = .left
        scoreLabel.position = CGPoint(x: frame.minX + 16, y: frame.maxY - 48)
        scoreLabel.zPosition = 10
        updateScoreLabel()
        addChild(scoreLabel)

        livesLabel = SKLabelNode(fontNamed: "Avenir-Heavy")
        livesLabel.fontSize = 18
        livesLabel.fontColor = SKColor(white: 0.9, alpha: 1.0)
        livesLabel.horizontalAlignmentMode = .right
        livesLabel.position = CGPoint(x: frame.maxX - 16, y: frame.maxY - 48)
        livesLabel.zPosition = 10
        updateLivesLabel()
        addChild(livesLabel)

        messageLabel = SKLabelNode(fontNamed: "Avenir-Heavy")
        messageLabel.fontSize = 30
        messageLabel.fontColor = .white
        messageLabel.position = CGPoint(x: frame.midX, y: frame.midY + 16)
        messageLabel.zPosition = 10
        messageLabel.isHidden = true
        addChild(messageLabel)

        subMessageLabel = SKLabelNode(fontNamed: "Avenir-Medium")
        subMessageLabel.fontSize = 18
        subMessageLabel.fontColor = SKColor(white: 0.7, alpha: 1.0)
        subMessageLabel.position = CGPoint(x: frame.midX, y: frame.midY - 20)
        subMessageLabel.zPosition = 10
        subMessageLabel.isHidden = true
        addChild(subMessageLabel)
    }

    // MARK: - Label Updates

    private func updateScoreLabel() {
        scoreLabel.text = "SCORE \(score)"
    }

    private func updateLivesLabel() {
        let hearts = String(repeating: "♥", count: lives)
        let emptyHearts = String(repeating: "♡", count: max(0, 3 - lives))
        livesLabel.text = hearts + emptyHearts
    }

    private func showMessage(_ text: String, sub: String = "") {
        messageLabel.text = text
        messageLabel.isHidden = false
        messageLabel.alpha = 0
        messageLabel.run(.fadeIn(withDuration: 0.3))

        if !sub.isEmpty {
            subMessageLabel.text = sub
            subMessageLabel.isHidden = false
            subMessageLabel.alpha = 0
            subMessageLabel.run(.sequence([
                .wait(forDuration: 0.15),
                .fadeIn(withDuration: 0.3),
                .repeatForever(.sequence([
                    .fadeAlpha(to: 0.4, duration: 0.8),
                    .fadeAlpha(to: 1.0, duration: 0.8),
                ]))
            ]))
        } else {
            subMessageLabel.isHidden = true
        }
    }

    private func hideMessage() {
        messageLabel.isHidden = true
        messageLabel.removeAllActions()
        subMessageLabel.isHidden = true
        subMessageLabel.removeAllActions()
    }

    // MARK: - Game Flow

    private func launchBall() {
        isPlaying = true
        hideMessage()

        let angle = CGFloat.random(in: CGFloat.pi / 4 ... CGFloat.pi * 3 / 4)
        let dx = ballSpeed * cos(angle)
        let dy = ballSpeed * sin(angle)
        ball.physicsBody?.velocity = CGVector(dx: dx, dy: dy)
    }

    private func resetBall() {
        ball.physicsBody?.velocity = .zero
        ball.position = CGPoint(x: frame.midX, y: paddle.position.y + 24)
        paddle.position.x = frame.midX
        isPlaying = false
    }

    private func loseLife() {
        lives -= 1
        updateLivesLabel()

        // Screen shake
        let shake = SKAction.sequence([
            .moveBy(x: 6, y: 0, duration: 0.03),
            .moveBy(x: -12, y: 0, duration: 0.03),
            .moveBy(x: 10, y: 0, duration: 0.03),
            .moveBy(x: -8, y: 0, duration: 0.03),
            .moveBy(x: 4, y: 0, duration: 0.03),
            .moveBy(x: 0, y: 0, duration: 0.03),
        ])

        let overlay = SKShapeNode(rect: frame)
        overlay.fillColor = SKColor(red: 1.0, green: 0.2, blue: 0.2, alpha: 0.3)
        overlay.strokeColor = .clear
        overlay.zPosition = 100
        addChild(overlay)
        overlay.run(.sequence([.fadeOut(withDuration: 0.4), .removeFromParent()]))

        if let cam = camera {
            cam.run(shake)
        } else {
            let cameraNode = SKCameraNode()
            cameraNode.position = CGPoint(x: frame.midX, y: frame.midY)
            addChild(cameraNode)
            camera = cameraNode
            cameraNode.run(shake)
        }

        if lives <= 0 {
            gameOver()
        } else {
            resetBall()
            showMessage("ミス!", sub: "タップして再開")
        }
    }

    private func gameOver() {
        resetBall()
        showMessage("ゲームオーバー", sub: "タップでリトライ")
    }

    private func gameClear() {
        resetBall()

        // Celebration particles
        for i in 0..<5 {
            let emitter = SKEmitterNode()
            emitter.particleBirthRate = 60
            emitter.numParticlesToEmit = 30
            emitter.particleLifetime = 1.5
            emitter.particleLifetimeRange = 0.5
            emitter.emissionAngle = CGFloat.pi / 2
            emitter.emissionAngleRange = CGFloat.pi / 3
            emitter.particleSpeed = 200
            emitter.particleSpeedRange = 100
            emitter.particleSize = CGSize(width: 6, height: 6)
            emitter.particleSizeRange = 4
            emitter.particleAlphaSpeed = -0.8
            emitter.particleColor = blockColors[i % blockColors.count].fill
            emitter.particleColorBlendFactor = 1.0
            emitter.particleBlendMode = .add
            emitter.position = CGPoint(
                x: frame.minX + frame.width * CGFloat(i + 1) / 6,
                y: frame.minY
            )
            emitter.zPosition = 50
            let yAccel: CGFloat = -300
            emitter.yAcceleration = yAccel
            addChild(emitter)
            emitter.run(.sequence([.wait(forDuration: 3.0), .removeFromParent()]))
        }

        showMessage("クリア! \(score)点", sub: "タップでリトライ")
    }

    private func resetGame() {
        score = 0
        lives = 3
        updateScoreLabel()
        updateLivesLabel()

        enumerateChildNodes(withName: "block") { node, _ in
            node.removeFromParent()
        }
        setupBlocks()
        resetBall()
    }

    // MARK: - Touch Handling

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        if !isPlaying {
            if lives <= 0 || blockCount <= 0 {
                resetGame()
            }
            launchBall()
            return
        }

        if let touch = touches.first {
            movePaddle(to: touch.location(in: self))
        }
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard isPlaying else { return }
        if let touch = touches.first {
            movePaddle(to: touch.location(in: self))
        }
    }

    private func movePaddle(to location: CGPoint) {
        let paddleWidth = frame.width * 0.24
        let halfWidth = paddleWidth / 2
        let clampedX = max(frame.minX + halfWidth, min(location.x, frame.maxX - halfWidth))
        paddle.run(.moveTo(x: clampedX, duration: 0.04))
    }

    // MARK: - Physics Contact

    func didBegin(_ contact: SKPhysicsContact) {
        let bodyA = contact.bodyA
        let bodyB = contact.bodyB
        let mask = bodyA.categoryBitMask | bodyB.categoryBitMask

        if mask == (Category.ball | Category.block) {
            let blockBody = bodyA.categoryBitMask == Category.block ? bodyA : bodyB
            if let blockNode = blockBody.node {
                destroyBlock(blockNode)
            }
        }

        if mask == (Category.ball | Category.bottom) {
            loseLife()
        }

        if mask == (Category.ball | Category.paddle) {
            adjustBallAngle()
        }
    }

    private func destroyBlock(_ node: SKNode) {
        let blockColor = (node as? SKShapeNode)?.fillColor ?? .white

        // Destruction particles
        let particles = SKEmitterNode()
        particles.particleBirthRate = 200
        particles.numParticlesToEmit = 12
        particles.particleLifetime = 0.5
        particles.particleLifetimeRange = 0.2
        particles.particleSpeed = 100
        particles.particleSpeedRange = 60
        particles.emissionAngleRange = CGFloat.pi * 2
        particles.particleSize = CGSize(width: 5, height: 5)
        particles.particleSizeRange = 3
        particles.particleAlpha = 0.9
        particles.particleAlphaSpeed = -2.0
        particles.particleColor = blockColor
        particles.particleColorBlendFactor = 1.0
        particles.particleBlendMode = .add
        particles.position = node.position
        particles.zPosition = 5
        addChild(particles)
        particles.run(.sequence([.wait(forDuration: 0.8), .removeFromParent()]))

        node.removeFromParent()
        blockCount -= 1

        // Score: higher rows = more points
        let rowPoints = [60, 50, 40, 30, 20, 10]
        let blockY = node.position.y
        let topOffset = frame.maxY - 120
        let rowIndex = Int((topOffset - blockY) / 22)
        score += rowPoints[min(rowIndex, rowPoints.count - 1)]
        updateScoreLabel()

        if blockCount <= 0 {
            gameClear()
        }
    }

    private func adjustBallAngle() {
        guard let velocity = ball.physicsBody?.velocity else { return }
        let offsetX = ball.position.x - paddle.position.x
        let paddleWidth = frame.width * 0.24
        let normalizedOffset = (offsetX / (paddleWidth / 2)).clamped(to: -1...1)
        let maxAngle: CGFloat = CGFloat.pi / 3
        let angle = normalizedOffset * maxAngle

        let speed = sqrt(velocity.dx * velocity.dx + velocity.dy * velocity.dy)
        let clampedSpeed = max(ballSpeed, speed)
        let dx = sin(angle) * clampedSpeed
        let dy = abs(cos(angle) * clampedSpeed)

        ball.physicsBody?.velocity = CGVector(dx: dx, dy: dy)
    }

    // MARK: - Update Loop

    override func update(_ currentTime: TimeInterval) {
        guard isPlaying, let velocity = ball.physicsBody?.velocity else { return }

        let speed = sqrt(velocity.dx * velocity.dx + velocity.dy * velocity.dy)

        // Keep ball speed consistent
        if speed < ballSpeed * 0.85 || speed > ballSpeed * 1.15 {
            let factor = ballSpeed / max(speed, 0.001)
            ball.physicsBody?.velocity = CGVector(
                dx: velocity.dx * factor,
                dy: velocity.dy * factor
            )
        }

        // Prevent nearly horizontal movement
        let minVerticalSpeed = ballSpeed * 0.25
        if abs(velocity.dy) < minVerticalSpeed {
            let sign: CGFloat = velocity.dy >= 0 ? 1 : -1
            let newDy = sign * minVerticalSpeed
            let newDx = sqrt(ballSpeed * ballSpeed - newDy * newDy) * (velocity.dx >= 0 ? 1 : -1)
            ball.physicsBody?.velocity = CGVector(dx: newDx, dy: newDy)
        }
    }
}

// MARK: - CGFloat Extension

private extension Comparable {
    func clamped(to range: ClosedRange<Self>) -> Self {
        min(max(self, range.lowerBound), range.upperBound)
    }
}
